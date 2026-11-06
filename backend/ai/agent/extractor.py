"""
PDF question extractor with robust header/footer removal, page-number stripping, and OCR fallback.
Extraction flow:
- Try pdfplumber word-level extraction grouped by Y to preserve symbols.
- Clean each page: strip very short lines, remove page-number/header patterns, detect repeated first/last lines across pages.
- If pdf text is empty or too sparse, render pages with PyMuPDF at high DPI and OCR via EasyOCR.
- Optionally pass cleaned text through an LLM cleaner (safe no-op by default) before question splitting.
"""
import os
import re
import time
import io
import base64
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .m import print_info, print_success, print_error, print_progress, save_json
import requests

# Load .env (best effort) so OLLAMA_API_URL / OLLAMA_MODEL / MATHPIX_* are available.
try:  # pragma: no cover - optional dependency
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# Optional imports with graceful degradation
try:
    import pdfplumber  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    pdfplumber = None  # type: ignore

try:
    import fitz  # PyMuPDF
except Exception:  # pragma: no cover - optional dependency
    fitz = None  # type: ignore

try:
    from PIL import Image  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    Image = None  # type: ignore


class QuestionExtractor:
    def __init__(self):
        # Local LLM (Ollama) configuration, overridable via environment.
        self.ollama_url = os.getenv("OLLAMA_API_URL", "http://localhost:11434").rstrip("/")
        self.model_name = os.getenv("OLLAMA_MODEL", "koesn/llama3-8b-instruct:latest")
        self.llm_enabled = True
        # MathPix credentials from env
        self.mathpix_app_id = os.getenv("MATHPIX_APP_ID")
        self.mathpix_app_key = os.getenv("MATHPIX_APP_KEY")

    # -----------------------
    # PDF Extraction (pdfplumber)
    # -----------------------
    def _words_to_lines(self, words: List[dict], y_tol: float = 2.0) -> List[str]:
        """Group pdfplumber words into lines by their baseline y coordinate.
        Keeps reading order left-to-right; merges small gaps into spaces.
        """
        if not words:
            return []
        # Group by rounded y coordinate
        rows: Dict[float, List[dict]] = defaultdict(list)
        for w in words:
            y = round(float(w.get("top", 0.0)) / y_tol) * y_tol
            rows[y].append(w)
        lines: List[str] = []
        for y in sorted(rows.keys()):
            row = sorted(rows[y], key=lambda w: float(w.get("x0", 0.0)))
            text_parts: List[str] = []
            prev_x1: Optional[float] = None
            for w in row:
                t = w.get("text", "")
                x0 = float(w.get("x0", 0.0))
                if prev_x1 is not None and x0 - prev_x1 > 3.0:
                    text_parts.append(" ")  # gap heuristic
                text_parts.append(t)
                prev_x1 = float(w.get("x1", x0))
            line = "".join(text_parts).strip()
            if line:
                lines.append(line)
        return lines

    def _extract_with_pdfplumber(self, file_path: str) -> List[List[str]]:
        """Return a list of pages, each a list of lines extracted via pdfplumber.

        Uses pdfplumber's layout-aware ``extract_text(layout=True)`` which keeps
        reading order and word spacing correct for the table-based VIT papers
        (the previous word-by-word grouping scrambled multi-column layouts).
        """
        if not pdfplumber:
            return []
        pages_lines: List[List[str]] = []
        try:
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    try:
                        lines = self._extract_page_lines(page)
                    except Exception:
                        raw = page.extract_text(x_tolerance=1.5, y_tolerance=3.0) or ""
                        lines = [l.strip() for l in raw.splitlines() if l.strip()]
                    pages_lines.append(lines)
        except Exception as e:
            print_error(f"pdfplumber failed on {os.path.basename(file_path)}: {e}")
            return []
        return pages_lines

    def _extract_page_lines(self, page) -> List[str]:
        """Read PDF text in visual order, using column order for two-column pages."""
        words = page.extract_words(x_tolerance=2, y_tolerance=3, keep_blank_chars=False) or []
        width = float(page.width)
        left = [word for word in words if float(word.get("x1", 0)) <= width * 0.48]
        right = [word for word in words if float(word.get("x0", width)) >= width * 0.52]
        if len(left) >= 8 and len(right) >= 8:
            left_text = page.crop((0, 0, width * 0.5, page.height)).extract_text(x_tolerance=2, y_tolerance=3) or ""
            right_text = page.crop((width * 0.5, 0, width, page.height)).extract_text(x_tolerance=2, y_tolerance=3) or ""
            if left_text.strip() and right_text.strip():
                raw = left_text + "\n" + right_text
                return [re.sub(r"\s+", " ", line).strip() for line in raw.splitlines() if line.strip()]
        raw = page.extract_text(layout=True) or ""
        return [re.sub(r"\s+", " ", line).strip() for line in raw.splitlines() if line.strip()]

    # -----------------------
    # OCR Fallback (PyMuPDF + EasyOCR)
    # -----------------------
    def _render_page_to_image(self, doc: "fitz.Document", page_index: int, dpi: int = 300):
        zoom = dpi / 72.0
        mat = fitz.Matrix(zoom, zoom)
        page = doc.load_page(page_index)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        return pix

    def _easyocr_to_lines(self, results: list, y_tol: int = 15) -> List[str]:
        """Convert EasyOCR bounding boxes to reading-order lines (top→bottom, left→right)."""
        if not results:
            return []
        from collections import defaultdict as _dd
        rows: Dict[int, List[tuple]] = _dd(list)
        for (bbox, text, conf) in results:
            if conf < 0.3 or not text.strip():
                continue
            top_y = int(bbox[0][1])
            row_key = (top_y // y_tol) * y_tol
            rows[row_key].append((float(bbox[0][0]), text.strip()))
        lines: List[str] = []
        for y in sorted(rows):
            sorted_row = sorted(rows[y], key=lambda x: x[0])
            line = " ".join(t for _, t in sorted_row).strip()
            if line:
                lines.append(line)
        return lines

    def _extract_with_ocr(self, file_path: str, dpi: int = 300) -> List[List[str]]:
        """EasyOCR-based extraction for scanned/image PDFs. No external binary required."""
        if not fitz:
            print_error("PyMuPDF (fitz) not installed.")
            return []
        try:
            import easyocr  # type: ignore
            import numpy as np  # type: ignore
        except ImportError:
            print_error("easyocr not installed. Run: pip install easyocr")
            return []

        print_info("Initialising EasyOCR (first run downloads ~100 MB model)...")
        reader = easyocr.Reader(['en'], gpu=False, verbose=False)
        pages_lines: List[List[str]] = []
        try:
            doc = fitz.open(file_path)
            for i in range(doc.page_count):
                try:
                    pix = self._render_page_to_image(doc, i, dpi=dpi)
                    # Reshape using the pixmap's actual channel count; drop alpha if present.
                    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
                    if pix.n == 4:
                        img = img[:, :, :3]
                    results = reader.readtext(img, detail=1, paragraph=False)
                    lines = self._easyocr_to_lines(results)
                except Exception as e:
                    print_error(f"EasyOCR failed on page {i + 1}: {e}")
                    lines = []
                pages_lines.append(lines)
            doc.close()
        except Exception as e:
            print_error(f"EasyOCR pass failed: {e}")
            return []
        return pages_lines

    # -----------------------
    # Cleaning headers/footers
    # -----------------------
    def _detect_repeated_edges(self, pages_lines: List[List[str]]) -> Tuple[Optional[str], Optional[str]]:
        """Detect repeated first and last lines across pages as headers/footers."""
        firsts = [next((l for l in p if l.strip()), "") for p in pages_lines if p]
        lasts = [next((l for l in reversed(p) if l.strip()), "") for p in pages_lines if p]
        n = max(len(firsts), len(lasts)) or 1
        header = None
        footer = None
        if firsts:
            c = Counter(firsts)
            text, count = c.most_common(1)[0]
            if text and count >= max(2, int(0.4 * n)):
                header = text
        if lasts:
            c = Counter(lasts)
            text, count = c.most_common(1)[0]
            if text and count >= max(2, int(0.4 * n)):
                footer = text
        return header, footer

    def _matches_page_artifact(self, line: str) -> bool:
        patterns = [
            r"^page\s*\d+\s*(of\s*\d+)?$",
            r"^\d+\s*/\s*\d+$",
            r"^\(\s*\d+\s*\)$",
            r"^(section|part)\s*[abcdefghijvix]+\b",
            r"^(instructions?|note[s]?):",
            r"^\*+\s*continued\s*\*+$",
            r"^vellore\s+institute|vit\b",
            r"^\d{4}-\d{2}|\bsemester\b|\bexam\b",
        ]
        s = line.strip().lower()
        if len(s) <= 2:
            return True
        for pat in patterns:
            if re.search(pat, s, flags=re.I):
                return True
        return False

    def _clean_pages(self, pages_lines: List[List[str]]) -> List[str]:
        header, footer = self._detect_repeated_edges(pages_lines)
        cleaned_all: List[str] = []
        for lines in pages_lines:
            page_clean: List[str] = []
            for l in lines:
                if len(l.strip()) <= 2:
                    continue  # (a) strip very short lines
                if self._matches_page_artifact(l):
                    continue  # (b) remove page numbers/headers
                page_clean.append(l)
            # (c) remove detected header/footer if present
            if header and page_clean and page_clean[0].strip() == header.strip():
                page_clean = page_clean[1:]
            if footer and page_clean and page_clean[-1].strip() == footer.strip():
                page_clean = page_clean[:-1]
            cleaned_all.extend(page_clean + [""])  # keep page break as empty line
        return cleaned_all

    # -----------------------
    # LLM cleaning hook (optional, safe no-op)
    # -----------------------
    def _llm_clean_text(self, text: str) -> str:
        """Override to integrate an LLM cleaner. Default: return input unchanged."""
        if not self.llm_enabled:
            return text
        try:
            prompt = (
                "You are a document cleaner for exam questions.\n"
                "Input is OCR/extracted text of an exam paper.\n"
                "Tasks:\n"
                "- Remove any remaining headers/footers, page numbers, watermarks.\n"
                "- Fix common OCR artifacts (broken hyphenation, wrong spaces).\n"
                "- Preserve math expressions faithfully (fractions, integrals, matrices).\n"
                "- Keep original question order and line breaks sensibly.\n"
                "Return the cleaned text only.\n\n"
                "Text:\n" + text
            )
            resp = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.2}
                },
                timeout=120,
            )
            if resp.status_code == 200:
                data = resp.json()
                cleaned = data.get("response", "")
                return cleaned.strip() or text
            else:
                print_error(f"Ollama cleaning failed: HTTP {resp.status_code}")
                return text
        except Exception as e:
            print_error(f"Ollama cleaning error: {e}")
            return text

    # -----------------------
    # LLM-based question extraction (Ollama)
    # -----------------------
    def _ollama_available(self) -> bool:
        """Return True if a local Ollama server is reachable."""
        try:
            r = requests.get(f"{self.ollama_url}/api/tags", timeout=3)
            return r.status_code == 200
        except Exception:
            return False

    @staticmethod
    def _parse_question_list(raw: str) -> List[str]:
        """Parse an LLM response into a clean list of question strings.

        Accepts a JSON array of strings, or a numbered/bulleted plain-text list.
        """
        raw = (raw or "").strip()
        if not raw:
            return []
        # Strip code fences if the model wrapped the output.
        raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.I | re.M).strip()

        # 1) Try to locate and parse a JSON array.
        m = re.search(r"\[.*\]", raw, flags=re.S)
        if m:
            try:
                arr = json.loads(m.group(0))
                if isinstance(arr, list):
                    items = [str(x).strip() for x in arr if str(x).strip()]
                    if items:
                        return items
            except Exception:
                pass

        # 2) Fall back to splitting a numbered/bulleted list.
        items: List[str] = []
        for line in raw.splitlines():
            line = line.strip()
            if not line:
                continue
            line = re.sub(r"^[-*•]\s*", "", line)        # bullets
            line = re.sub(r"^\(?\d+[\.\)]\s*", "", line)        # 1.  1)  (1)
            line = re.sub(r"^Q(uestion)?\s*\d+[:\.\)]?\s*", "", line, flags=re.I)
            if len(line) > 10:
                items.append(line.strip())
        return items

    def _llm_extract_questions(self, text: str, topic: str = "") -> List[str]:
        """Use the local LLM to extract every distinct question, verbatim.

        Returns [] on any failure so the caller can fall back to the heuristic
        parser.
        """
        if not text.strip():
            return []
        topic_clause = (
            f"\nOnly include questions related to the topic: '{topic}'. "
            "If none relate, return an empty array.\n" if topic else "\n"
        )
        prompt = (
            "You are extracting exam questions from the messy OCR/extracted text of "
            "a university exam paper.\n"
            "Extract EVERY distinct question and sub-question (a, b, c, i, ii ...) "
            "asked in the paper.\n"
            "Rules:\n"
            "- Reproduce each question's wording faithfully; fix only obvious OCR "
            "spacing/hyphenation errors.\n"
            "- Treat each labelled sub-part as its own separate question.\n"
            "- IGNORE headers, footers, institute names, instructions, course "
            "outcomes, marks, CO/BL columns, and page numbers.\n"
            "- Do NOT invent questions or add commentary.\n"
            f"{topic_clause}"
            "Return ONLY a JSON array of strings, one string per question, with no "
            "other text.\n\n"
            "PAPER TEXT:\n" + text
        )
        # Try up to twice: the first call may hit a cold model load that returns
        # an empty/odd response before the weights are resident in memory.
        questions: List[str] = []
        for attempt in range(2):
            try:
                resp = requests.post(
                    f"{self.ollama_url}/api/generate",
                    json={
                        "model": self.model_name,
                        "prompt": prompt,
                        "stream": False,
                        "options": {"temperature": 0.1, "num_ctx": 8192},
                    },
                    timeout=300,
                )
                if resp.status_code != 200:
                    print_error(f"Ollama extraction failed: HTTP {resp.status_code}")
                    return []
                response_text = resp.json().get("response", "")
            except Exception as e:
                print_error(f"Ollama extraction error: {e}")
                return []
            questions = self._parse_question_list(response_text)
            if questions:
                break
        # Light cleanup + dedupe while preserving order.
        seen = set(); out: List[str] = []
        for q in questions:
            q = re.sub(r"\s+", " ", q).strip()
            if len(q) > 10 and q.lower() not in seen:
                seen.add(q.lower()); out.append(q)
        return out

    # -----------------------
    # MathPix OCR pass (optional)
    # -----------------------
    def _mathpix_available(self) -> bool:
        return bool(self.mathpix_app_id and self.mathpix_app_key and fitz)

    def _img_to_data_uri(self, pil_img: "Image") -> str:
        buf = io.BytesIO()
        pil_img.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode("ascii")
        return f"data:image/png;base64,{b64}"

    def _extract_with_mathpix(self, file_path: str, dpi: int = 300) -> List[List[str]]:
        """Render each page and send to MathPix v3/text. Returns per-page lines."""
        if not (self._mathpix_available() and Image):
            return []
        pages_lines: List[List[str]] = []
        headers = {
            "app_id": self.mathpix_app_id or "",
            "app_key": self.mathpix_app_key or "",
            "Content-type": "application/json",
        }
        try:
            doc = fitz.open(file_path)
            for i in range(doc.page_count):
                try:
                    pix = self._render_page_to_image(doc, i, dpi=dpi)
                    mode = "RGBA" if pix.n == 4 else "RGB"
                    img = Image.frombytes(mode, [pix.width, pix.height], pix.samples)
                    if mode == "RGBA":
                        img = img.convert("RGB")
                    src = self._img_to_data_uri(img)
                    payload = {
                        "src": src,
                        "formats": ["text"],
                        "data_options": {
                            "include_asciimath": False,
                            "include_latex": True
                        },
                        "math_inline_delimiters": ["$", "$"],
                        "rm_spaces": True,
                    }
                    r = requests.post("https://api.mathpix.com/v3/text", headers=headers, data=json.dumps(payload), timeout=120)
                    if r.status_code == 200:
                        data = r.json()
                        text = data.get("text", "")
                        lines = [l.strip() for l in text.splitlines() if l.strip()]
                    else:
                        print_error(f"MathPix page {i+1} failed: HTTP {r.status_code}")
                        lines = []
                except Exception as e:
                    print_error(f"MathPix error on page {i+1}: {e}")
                    lines = []
                pages_lines.append(lines)
            doc.close()
        except Exception as e:
            print_error(f"MathPix pass failed: {e}")
            return []
        return pages_lines

    # -----------------------
    # Question splitting and filtering
    # -----------------------
    # Imperative/interrogative verbs that begin VIT exam questions.
    _QUESTION_STARTERS = (
        "discuss", "calculate", "explain", "compare", "highlight", "define",
        "describe", "list", "derive", "write", "state", "give", "find",
        "determine", "show", "prove", "illustrate", "mention", "differentiate",
        "outline", "analyse", "analyze", "evaluate", "draw", "identify",
        "what", "why", "how", "when", "where", "which", "who", "whom",
        "whose", "is", "are", "was", "were", "do", "does", "did", "can",
        "could", "would", "should", "will", "shall", "obtain", "construct",
        "compute", "design", "estimate", "justify", "interpret", "summarize",
        "trace", "perform", "assess", "comment", "implement", "examine",
        "given", "suppose", "assuming", "using", "based",
        "discuss", "calculate", "explain", "compare", "highlight", "define",
        "describe", "list", "derive", "write", "state", "give", "find",
        "determine", "show", "prove", "illustrate", "mention", "differentiate",
        "outline", "analyse", "analyze", "evaluate", "draw", "identify",
    )

    _LABEL_RE = re.compile(
        r"^\s*(?P<label>(?:\(?\d{1,2}\)?[.)]|\(?[a-z]\)?[.)]|\(?[ivxlcdm]{1,5}\)?[.)]))\s*(?P<body>.*)$",
        re.I,
    )
    _NUMBERED_RE = re.compile(r"^\s*(?:Q(?:uestion)?\s*)?\d{1,2}\s*[.) :]\s*(?P<body>.+)$", re.I)

    def _strip_marks_tokens(self, line: str) -> str:
        """Remove trailing mark/CO/BL columns the layout text leaves on a line.

        VIT papers put 'M CO BL' columns to the right of each question, so layout
        extraction appends tokens like ' 4 2', ' 10', or ' 4 3' to question lines.
        """
        # Drop trailing runs of standalone 1-2 digit numbers (mark columns).
        return re.sub(r"(\s+\d{1,2}){1,3}\s*$", "", line).strip()

    def _clean_question_text(self, q: str) -> str:
        q = re.sub(r"\s+", " ", q).strip()
        q = self._question_body(q)
        q = re.sub(r"^(Q|Question)\s*\d+[:\.)]?\s*", "", q, flags=re.I)
        q = re.sub(r"\[?\(?\s*\d+\s*(marks?|pts?|points?)\s*\)?\]?$", "", q, flags=re.I).strip()
        q = self._strip_marks_tokens(q)
        if q and q[-1] not in ".?!":
            if q.lower().startswith(("what", "why", "how", "when", "where",
                                     "which", "who", "is ", "are ", "do ", "does ",
                                     "can ", "could ", "would ", "should ")):
                q = q + "?"
        return q.strip()

    def _is_question_start(self, line: str) -> bool:
        s = line.strip()
        match = self._NUMBERED_RE.match(s) or self._LABEL_RE.match(s)
        if match:
            s = match.group("body").strip()
        first = re.split(r"\W+", s.lower(), maxsplit=1)
        return bool(first and first[0] in self._QUESTION_STARTERS)

    def _is_subquestion_start(self, line: str) -> bool:
        match = self._LABEL_RE.match(line.strip())
        if not match or not match.group("body").strip():
            return False
        body = match.group("body").strip()
        return self._is_question_start(body) or len(body) >= 20

    def _question_body(self, line: str) -> str:
        match = self._NUMBERED_RE.match(line.strip()) or self._LABEL_RE.match(line.strip())
        return match.group("body").strip() if match else line.strip()

    def _is_noise_line(self, line: str) -> bool:
        s = line.strip().lower()
        if re.fullmatch(r"[\d\s\.\)\(/:-]*", s):  # pure numbers / separators
            return True
        if re.match(r"^q(?:uestion)?\s*\d+\s*[:.)-]", s):
            return False
        noise = (
            "qn", "question", "m cobl", "m co bl", "answer all",
            "max mark", "course outcome", "co-", "blooms", "bl -",
            "general instruction", "programme name", "course code",
            "faculty name", "class, number", "date of examination",
            "exam duration", "maximum marks", "school of", "slot:",
            "continuous assessment", "fall semester", "winter semester",
            "vellore institute", "vit",
        )
        return any(s.startswith(n) or n in s for n in noise) and len(s) < 80

    def _extract_vit_questions(self, lines: List[str]) -> List[str]:
        questions: List[str] = []
        buffer = ""
        for raw in lines:
            line = self._strip_marks_tokens(raw.strip())
            if not line or self._is_noise_line(line):
                continue
            if self._is_question_start(line) or self._is_subquestion_start(line):
                if buffer:
                    questions.append(buffer.strip())
                buffer = self._question_body(line)
            elif buffer and line.endswith(("?", ".", ":")):
                questions.append((buffer + " " + line).strip())
                buffer = ""
            elif buffer:
                # Continuation of the current question.
                buffer += " " + line
        if buffer:
            questions.append(buffer.strip())
        # Clean, keep only substantive items, and dedupe.
        cleaned = [self._clean_question_text(q) for q in questions if len(q) > 15]
        seen = set(); out: List[str] = []
        for q in cleaned:
            if len(q) > 15 and q not in seen:
                seen.add(q); out.append(q)
        return out

    def _filter_by_topic(self, questions: List[str], topic: str) -> List[str]:
        if not topic:
            return questions
        kws = [w.lower() for w in re.split(r"\W+", topic) if w]
        out = []
        for q in questions:
            lower = q.lower()
            if any(k in lower for k in kws):
                out.append(q)
        return out

    # -----------------------
    # Public API
    # -----------------------
    def extract_questions(self, file_path: str, topic: str, use_llm: bool = True, use_mathpix: bool = False) -> List[str]:
        print_progress("Extracting (pdfplumber)...")
        pages_lines = self._extract_with_pdfplumber(file_path)
        # If plumber failed or produced too little content, OCR fallback.
        # Use avg chars/page — scanned PDFs often return a few header chars but nothing useful.
        total_chars = sum(len(l) for p in pages_lines for l in p)
        avg_chars = total_chars / max(len(pages_lines), 1)
        if not pages_lines or avg_chars < 150:
            if use_mathpix and self._mathpix_available():
                print_info("Falling back to MathPix OCR (best for math)...")
                pages_lines = self._extract_with_mathpix(file_path)
            else:
                print_info("Falling back to OCR (high-DPI render + EasyOCR)...")
                pages_lines = self._extract_with_ocr(file_path)

        if not pages_lines:
            print_error("No text could be extracted from the PDF.")
            return []

        print_progress("Cleaning headers/footers and artifacts...")
        cleaned_lines = self._clean_pages(pages_lines)
        text = "\n".join(cleaned_lines)

        # Primary path: let a local LLM extract every question cleanly. Fall back
        # to the heuristic parser if the LLM is unavailable or returns nothing.
        questions: List[str] = []
        if use_llm and self.llm_enabled and self._ollama_available():
            print_progress(f"Extracting questions via LLM ({self.model_name})...")
            questions = self._llm_extract_questions(text, topic)
            if questions:
                print_success(f"Extracted {len(questions)} questions (LLM) from {os.path.basename(file_path)}")
                return questions
            print_info("LLM returned nothing; falling back to heuristic parser.")

        print_progress("Parsing questions (heuristic)...")
        questions = self._extract_vit_questions(text.splitlines())
        filtered = self._filter_by_topic(questions, topic)
        print_success(f"Extracted {len(filtered)} questions from {os.path.basename(file_path)}")
        return filtered

    def extract_from_multiple_papers(self, file_paths: List[str], topic: str, use_llm: bool = True, use_mathpix: bool = False) -> dict:
        results = {
            'papers_processed': 0,
            'total_questions': 0,
            'questions_by_paper': {},
            'combined_questions': [],
            'failed_papers': []
        }
        for f in file_paths:
            try:
                qs = self.extract_questions(f, topic, use_llm=use_llm, use_mathpix=use_mathpix)
                results['papers_processed'] += 1
                results['total_questions'] += len(qs)
                results['questions_by_paper'][os.path.basename(f)] = qs
                results['combined_questions'].extend(qs)
            except Exception as e:
                results['failed_papers'].append({'file': f, 'error': str(e)})
        # dedupe
        seen = set(); combined: List[str] = []
        for q in results['combined_questions']:
            if q not in seen:
                seen.add(q); combined.append(q)
        results['combined_questions'] = combined
        results['unique_questions'] = len(combined)
        return results

    def save_questions(self, questions: List[str], topic: str, subject: str, save_path: str):
        data = {
            'metadata': {
                'subject': subject,
                'topic': topic,
                'question_count': len(questions),
                'extracted_at': time.strftime('%Y-%m-%d %H:%M:%S')
            },
            'questions': []
        }
        for q in questions:
            data['questions'].append({
                'text': q,
                'word_count': len(q.split()),
                'question_type': 'open' if '?' in q else 'statement'
            })
        save_json(data, save_path)

