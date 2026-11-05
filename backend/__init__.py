"""Backend package: minimal Flask app factory exposing the scrape -> extract pipeline."""
from flask import Flask, jsonify, request


def create_app():
    app = Flask(__name__)

    @app.get("/health")
    def health():
        return jsonify(status="ok")

    @app.post("/extract")
    def extract():
        """Scrape papers for a subject/topic and extract questions from them.

        JSON body: {"subject": str, "topic": str (optional), "max_papers": int (optional)}
        """
        # Imported lazily so the heavy scraping/OCR deps load only when this
        # endpoint is hit (and the app can still boot without them installed).
        from backend.ai.agent.scraper import ExamScraper
        from backend.ai.agent.extractor import QuestionExtractor

        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return jsonify(error="Request body must be a JSON object."), 400
        subject = data.get("subject")
        if not isinstance(subject, str) or not subject.strip():
            return jsonify(error="'subject' must be a non-empty string."), 400
        subject = subject.strip()
        topic = data.get("topic", "")
        if topic is None:
            topic = ""
        if not isinstance(topic, str):
            return jsonify(error="'topic' must be a string."), 400
        topic = topic.strip()
        max_papers = data.get("max_papers", 10)
        if isinstance(max_papers, bool) or not isinstance(max_papers, int):
            return jsonify(error="'max_papers' must be an integer between 1 and 20."), 400
        if not 1 <= max_papers <= 20:
            return jsonify(error="'max_papers' must be between 1 and 20."), 400

        scraper = ExamScraper()
        paper_paths = scraper.scrape_papers(subject, topic=topic, max_papers=max_papers)
        if not paper_paths:
            return jsonify(subject=subject, topic=topic, papers=[], questions=[],
                           message="No papers found"), 200

        extractor = QuestionExtractor()
        results = extractor.extract_from_multiple_papers(paper_paths, topic=topic)
        return jsonify(subject=subject, topic=topic, **results), 200

    return app
