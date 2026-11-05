#!/usr/bin/env python3
"""
Utility script: extract questions from all PDFs in data/raw_papers and save results.

Run as a package from the repo root so the package-relative imports resolve:
    python -m backend.ai.agent.run_extract_all
"""
import json
from pathlib import Path

from backend.ai.agent.extractor import QuestionExtractor
from backend.ai.agent.m import setup_directories, print_info, print_success, print_error

# Anchor paths on this file so the script works from any working directory.
AGENT_DIR = Path(__file__).resolve().parent


def main() -> int:
    setup_directories()
    data_dir = AGENT_DIR / 'data' / 'raw_papers'
    if not data_dir.exists():
        print_error(f'No {data_dir} directory found')
        return 1
    files = list(data_dir.glob('*.pdf'))
    if not files:
        print_error(f'No PDF files found in {data_dir}')
        return 1
    print_info(f'Found {len(files)} PDF(s) to process')
    extractor = QuestionExtractor()
    results = extractor.extract_from_multiple_papers([str(p) for p in files], topic='')
    out_path = AGENT_DIR / 'outputs' / 'extracted_questions_all.json'
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print_success(f'Saved extraction results to {out_path}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
