"""
Scraper for CodeChef-VIT exam papers.

The site (papers.codechefvit.com) is a Next.js app whose catalogue is backed by a
public JSON API:

    GET https://www.papers.codechefvit.com/api/papers?subject=<subject>

Each paper record contains a direct ``file_url`` pointing at the PDF on Google
Cloud Storage, so we can discover and download papers with plain HTTP requests --
no headless browser or HTML scraping required.
"""
import os
from pathlib import Path
from typing import List, Optional

from .m import print_info, print_success, print_error, print_progress, clean_filename

API_BASE = "https://www.papers.codechefvit.com/api"


class ExamScraper:
    def __init__(self, headless: Optional[bool] = None, debug: bool = False):
        import requests
        self.requests = requests
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        # Anchor the download dir on this file so it works regardless of CWD and
        # matches where the existing sample papers already live.
        self.download_dir = Path(__file__).resolve().parent / "data" / "raw_papers"
        self.debug = debug
        # Kept for backwards compatibility; no browser is used anymore.
        self.headless = headless

    # -----------------------
    # Discovery via the JSON API
    # -----------------------
    def _fetch_papers(self, subject: Optional[str] = None) -> List[dict]:
        """Query the papers API and return a normalised list of paper dicts.

        Each returned dict has: url (direct PDF), title, text (for filtering),
        subject, year, exam, slot, semester.
        """
        params = {}
        if subject:
            params['subject'] = subject
        try:
            resp = self.session.get(f"{API_BASE}/papers", params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print_error(f"Failed to query papers API: {e}")
            return []

        raw = data.get('papers', []) if isinstance(data, dict) else data
        if not isinstance(raw, list):
            print_error("Papers API returned an unexpected response format")
            return []
        papers: List[dict] = []
        for p in raw:
            if not isinstance(p, dict):
                continue
            file_url = p.get('file_url')
            if not isinstance(file_url, str) or not file_url.startswith(("https://", "http://")):
                continue
            subj = p.get('subject', subject or 'Unknown')
            exam = p.get('exam', '')
            year = p.get('year', '')
            slot = p.get('slot', '')
            sem = p.get('semester', '')
            title = ' '.join(part for part in [subj, exam, slot, year] if part).strip()
            papers.append({
                'url': file_url,
                'title': title or os.path.basename(file_url),
                'text': ' '.join([subj, exam, slot, year, sem]),
                'subject': subj,
                'year': year,
                'exam': exam,
                'slot': slot,
                'semester': sem,
            })
        if self.debug:
            print_info(f"API returned {len(papers)} paper(s) for subject={subject!r}")
        return papers

    def _filter_papers_by_topic(self, papers: List[dict], topic: Optional[str]) -> List[dict]:
        if not topic:
            return papers
        t = topic.lower()
        words = [w for w in t.split() if w]
        out = []
        for p in papers:
            txt = (p.get('title', '') + ' ' + p.get('text', '')).lower()
            if t in txt or any(w in txt for w in words):
                out.append(p)
        return out

    # -----------------------
    # Downloading
    # -----------------------
    def _download_paper(self, paper_info: dict) -> Optional[str]:
        url = paper_info.get('url')
        if not url:
            return None

        # Append the unique id from the URL so papers with identical
        # subject/exam/slot/year metadata don't collapse to one filename.
        uid = os.path.splitext(os.path.basename(url))[0]
        base = clean_filename(paper_info.get('title', '')) or 'paper'
        fname = f"{base}_{uid}.pdf" if uid else f"{base}.pdf"
        path = self.download_dir / fname

        if path.exists():
            if path.is_file() and path.stat().st_size > 0:
                print_info(f"Paper already exists: {path}")
                return str(path)
            path.unlink(missing_ok=True)

        print_progress(f"Downloading {fname}...")
        try:
            with self.session.get(url, stream=True, timeout=60) as resp:
                resp.raise_for_status()
                with open(path, 'wb') as f:
                    for chunk in resp.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
            if not path.is_file() or path.stat().st_size == 0:
                raise ValueError("Download returned an empty file")
            print_success(f"Saved paper to {path}")
            return str(path)
        except Exception as e:
            print_error(f"Failed to download {url}: {e}")
            if path.exists():
                path.unlink()  # clean up partial download
            return None

    # -----------------------
    # Public API
    # -----------------------
    def list_available_subjects(self) -> List[str]:
        """Return the distinct subjects available in the catalogue."""
        papers = self._fetch_papers()
        return sorted({p.get('subject', '') for p in papers if p.get('subject')})

    def scrape_papers(self, subject: str, topic: str = None, max_papers: int = 10) -> List[str]:
        if not isinstance(subject, str) or not subject.strip():
            print_error("Subject must be a non-empty string")
            return []
        if isinstance(max_papers, bool) or not isinstance(max_papers, int) or max_papers < 1:
            print_error("Maximum papers must be a positive integer")
            return []
        subject = subject.strip()
        topic = topic.strip() if isinstance(topic, str) else None
        print_info(f"Searching for papers in subject: {subject}")
        self.download_dir.mkdir(parents=True, exist_ok=True)

        papers = self._fetch_papers(subject)
        if not papers:
            print_error('No papers discovered for the subject')
            return []

        filtered = self._filter_papers_by_topic(papers, topic)
        if not filtered:
            print_info('No matching papers after topic filtering')
            return []

        print_success(f"Found {len(filtered)} matching papers")
        results = []
        for p in filtered[:max_papers]:
            fp = self._download_paper(p)
            if fp:
                results.append(fp)
        return results
