# 🚀 Quick Start Guide

## Fastest Way to Get Started

### 1️⃣ Install Dependencies
```bash
pip install -r requirements.txt
playwright install
```

### 2️⃣ Setup (First Time Only)
```bash
# Copy environment template
cp .env.example .env

# Install Tesseract OCR (Windows)
# Download from: https://github.com/UB-Mannheim/tesseract/wiki
# Or on macOS: brew install tesseract
# Or on Linux: sudo apt install tesseract-ocr
```

### 3️⃣ Run Interactive Menu
```bash
python main_demo.py
```

Choose from menu:
- **Option 3**: Scrape papers → Download PDFs to `backend/ai/agent/data/raw_papers/`
- **Option 4**: Extract questions → Save to `backend/ai/agent/outputs/extracted_questions_all.json`

---

## Command Line (Non-Interactive)

### Scrape Papers Only
```bash
cd backend/ai/agent
python -c "from scraper import ExamScraper; scraper = ExamScraper(); scraper.scrape_papers('Computer Science', max_papers=5)"
```

### Extract Questions Only
```bash
cd backend/ai/agent
python run_extract_all.py
```

### View Results
```bash
cat backend/ai/agent/outputs/extracted_questions_all.json
```

---

## For GitHub Upload

### Files to Commit
✅ `main_demo.py`
✅ `requirements.txt`
✅ `.env.example` (template only)
✅ `.gitignore` (prevents .env upload)
✅ `README.md`
✅ All source files in `backend/`

### Files NOT to Commit
❌ `.env` (has your API keys!)
❌ `backend/ai/agent/data/raw_papers/` (PDFs are large)
❌ `backend/ai/agent/outputs/` (generated results)
❌ `__pycache__/`
❌ `venv/`

### Push to GitHub Safely
```bash
# Make sure .env is in .gitignore
git status  # Verify .env is not listed

# Add and commit
git add .
git commit -m "Add exam paper scraper and question extractor"
git push origin main
```

---

## Troubleshooting

### ImportError: No module named 'tesseract'
Install Tesseract OCR from: https://github.com/UB-Mannheim/tesseract/wiki

### No papers found
Try different subject names or check if the website structure changed

### Questions extraction returns 0 results
- PDFs might be scanned images (needs OCR)
- Install Tesseract and try again
- Or use MathPix OCR for better results

---

## Optional: Enable Advanced Features

### LLM-based Cleaning (Local, Free)
```bash
# 1. Install Ollama: https://ollama.ai
# 2. Run in terminal: ollama serve
# 3. In another terminal: ollama pull koesn/llama3-8b-instruct:latest
# 4. Edit .env: USE_LLM_CLEANING=true
```

### MathPix OCR (For Math-Heavy Papers)
```bash
# 1. Get API key: https://www.mathpix.com
# 2. Edit .env with your credentials
# 3. Set: USE_MATHPIX=true
```

---

## Directory Structure
```
├── main_demo.py              ← Run this!
├── requirements.txt          ← Install these
├── .env.example             ← Copy to .env locally
├── .gitignore              ← Prevent sensitive files
├── backend/ai/agent/
│   ├── scraper.py          ← Downloads papers
│   ├── extractor.py        ← Extracts questions
│   ├── run_extract_all.py  ← Batch processing
│   ├── data/raw_papers/    ← PDFs saved here
│   └── outputs/            ← Results saved here
└── README.md
```

---

## Common Commands

| Task | Command |
|------|---------|
| Full setup | `pip install -r requirements.txt && playwright install` |
| Run menu | `python main_demo.py` |
| Scrape papers | Option 3 in menu, OR `cd backend/ai/agent && python -c "from scraper import ExamScraper; ExamScraper().scrape_papers('Computer Science', max_papers=5)"` |
| Extract questions | Option 4 in menu, OR `cd backend/ai/agent && python run_extract_all.py` |
| View results | `cat backend/ai/agent/outputs/extracted_questions_all.json` |
| Check git status | `git status` (verify .env not listed) |

Happy scraping! 📚
