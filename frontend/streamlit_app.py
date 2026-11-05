"""
Streamlit frontend for the Lecture-to-Notes / VIT exam-paper question extractor.

Run from the project root:
    streamlit run frontend/streamlit_app.py

It drives the scrape -> extract pipeline directly (no separate Flask server needed).
"""
import sys
import json
from pathlib import Path

import streamlit as st

# Make the `backend` package importable when Streamlit runs this file directly.
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.ai.agent.scraper import ExamScraper
from backend.ai.agent.extractor import QuestionExtractor

st.set_page_config(page_title="VIT Paper Question Extractor", page_icon="📝", layout="wide")

st.title("📝 Exam Paper Question Extractor")
st.caption("Scrapes past papers from papers.codechefvit.com and extracts the questions.")

with st.sidebar:
    st.header("Search")
    subject = st.text_input("Subject", value="engineering chemistry",
                            help="e.g. 'engineering chemistry', 'physics', 'data structures'")
    topic = st.text_input("Topic filter (optional)",
                          help="Only keep questions/papers mentioning this topic")
    max_papers = st.slider("Max papers", 1, 20, 5)
    use_llm = st.checkbox("Use LLM extraction (local Ollama)", value=True,
                          help="Cleaner, complete question lists. Falls back to the "
                               "heuristic parser automatically if Ollama isn't running.")
    run = st.button("🔍 Find & Extract", type="primary", use_container_width=True)


@st.cache_data(show_spinner=False)
def run_pipeline(subject: str, topic: str, max_papers: int, use_llm: bool) -> dict:
    scraper = ExamScraper()
    try:
        paths = scraper.scrape_papers(subject, topic=topic or None, max_papers=max_papers)
    except Exception as exc:
        return {"papers": [], "results": None, "error": f"Could not search/download papers: {exc}"}
    if not paths:
        return {"papers": [], "results": None,
                "error": "No papers were found. Check the subject spelling or try a broader search."}
    extractor = QuestionExtractor()
    try:
        results = extractor.extract_from_multiple_papers(paths, topic=topic, use_llm=use_llm)
    except Exception as exc:
        return {"papers": paths, "results": None, "error": f"Question extraction failed: {exc}"}
    return {"papers": paths, "results": results}


if run:
    if not subject.strip():
        st.error("Please enter a subject.")
        st.stop()

    with st.status("Scraping papers and extracting questions…", expanded=True) as status:
        st.write(f"Searching for **{subject}** papers…")
        try:
            data = run_pipeline(subject.strip(), topic.strip(), max_papers, use_llm)
        except Exception as e:  # surface any pipeline failure to the user
            status.update(label="Failed", state="error")
            st.error(f"Pipeline failed: {e}")
            st.stop()

        if not data["papers"]:
            if data.get("error"):
                status.update(label="Failed", state="error")
                st.error(data["error"])
                st.stop()
            status.update(label="No papers found", state="error")
            st.warning("No papers were found for that subject. Try a different spelling.")
            st.stop()
        status.update(label=f"Done — processed {len(data['papers'])} paper(s)", state="complete")

    if data.get("error") or data.get("results") is None:
        st.error(data.get("error", "Extraction did not return results."))
        st.stop()

    results = data["results"]
    c1, c2, c3 = st.columns(3)
    c1.metric("Papers processed", results.get("papers_processed", 0))
    c2.metric("Total questions", results.get("total_questions", 0))
    c3.metric("Unique questions", results.get("unique_questions", 0))

    st.subheader("Questions by paper")
    by_paper = results.get("questions_by_paper", {})
    if not any(by_paper.values()):
        st.info("Papers were downloaded but no questions could be parsed from them "
                "(scanned/low-quality scans or an unusual layout).")
    for paper, qs in by_paper.items():
        with st.expander(f"📄 {paper} — {len(qs)} question(s)", expanded=bool(qs)):
            if qs:
                for i, q in enumerate(qs, 1):
                    st.markdown(f"**{i}.** {q}")
            else:
                st.caption("No questions parsed from this paper.")

    if results.get("failed_papers"):
        st.subheader("Failed papers")
        for fp in results["failed_papers"]:
            st.error(f"{fp.get('file')}: {fp.get('error')}")

    st.download_button(
        "⬇️ Download results as JSON",
        data=json.dumps(results, indent=2, ensure_ascii=False),
        file_name=f"questions_{subject.strip().replace(' ', '_')}.json",
        mime="application/json",
    )
else:
    st.info("Enter a subject in the sidebar and click **Find & Extract** to begin.")
