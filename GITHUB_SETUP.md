# 📤 GitHub Upload & Deployment Guide

## Files Created for You

✅ **.env.example** - Environment template (safe to commit)
✅ **.gitignore** - Prevents secrets from being uploaded
✅ **setup.py** - Automated setup script
✅ **QUICK_START.md** - Fast reference guide
✅ **Updated README.md** - Complete documentation

---

## Complete Workflow: Scrape → Extract → Push to GitHub

### Step 1: Initial Setup

```bash
# Run setup script (one time)
python setup.py

# Or manually:
# - Copy .env.example to .env for local use only
# - Create directories manually if needed
```

### Step 2: Download Papers & Extract Questions

#### Option A: Interactive Menu (Recommended)
```bash
python main_demo.py

# Menu:
# 1. PDF Summarization
# 2. PowerPoint Summarization
# 3. Scrape Papers from CodeChef VIT  ← Choose this
# 4. Extract Questions from PDFs      ← Then this
# 5. Exit

# When prompted:
# - Subject: "Computer Science" (or any subject)
# - Topic: (press Enter to skip)
# - Max papers: 5 (or more)
```

#### Option B: Command Line
```bash
# Scrape papers
cd backend/ai/agent
python -c "
from scraper import ExamScraper
scraper = ExamScraper()
papers = scraper.scrape_papers('Computer Science', max_papers=5)
print(f'Downloaded {len(papers)} papers')
"

# Extract questions (run from the repository root)
python -m backend.ai.agent.run_extract_all

# View results (run from the repository root)
Get-Content backend/ai/agent/outputs/extracted_questions_all.json  # PowerShell
# macOS/Linux: cat backend/ai/agent/outputs/extracted_questions_all.json
```

### Step 3: Prepare for GitHub

#### Update .env.example with your settings (if using advanced features)
```bash
# Edit .env.example to include any custom configurations
# DO NOT put actual API keys in .env.example
# Leave them empty with comments
```

#### Verify .gitignore is correct
```bash
git status

# Should NOT show:
# - .env (your local secrets)
# - backend/ai/agent/data/raw_papers/*.pdf (large files)
# - __pycache__/
# - venv/
```

### Step 4: Push to GitHub

#### Initialize Git (if not already done)
```bash
git init
git add .
git commit -m "Initial commit: VIT exam paper scraper and question extractor"
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
git push -u origin main
```

#### Or if repository already exists
```bash
git add .
git status  # Verify .env is NOT listed!
git commit -m "Add scraper and extractor with setup guide"
git push
```

#### Verify safe upload
```bash
# On GitHub, verify:
# ✓ .env.example is present (template)
# ✓ .env is NOT present (not uploaded)
# ✓ QUICK_START.md is visible
# ✓ Updated README.md shows new commands
```

---

## What Each File Does

### Configuration Files

| File | Purpose | Commit to Git? |
|------|---------|---|
| `.env` | Your local secrets (API keys) | ❌ NO (in .gitignore) |
| `.env.example` | Template for others | ✅ YES |
| `.gitignore` | Prevent uploading secrets | ✅ YES |

### Documentation

| File | Purpose |
|------|---------|
| `README.md` | Main documentation (updated with new commands) |
| `QUICK_START.md` | Fast reference for common tasks |
| `setup.py` | Automated initial setup |

### Scripts

| File | Purpose |
|------|---------|
| `main_demo.py` | Interactive menu for all features |
| `requirements.txt` | Python dependencies |
| `backend/ai/agent/scraper.py` | Download papers |
| `backend/ai/agent/extractor.py` | Extract questions from PDFs |
| `backend/ai/agent/run_extract_all.py` | Batch question extraction |
| `backend/ai/agent/m.py` | Utility functions |

---

## Copy-Paste Command Sequences

### For First-Time Users (Fork from GitHub)

```bash
# 1. Clone your repo
git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git
cd YOUR_REPO

# 2. Setup
python setup.py

# 3. Copy environment (creates .env from .env.example)
cp .env.example .env

# 4. Install dependencies
pip install -r requirements.txt
playwright install

# 5. Install Tesseract OCR
# Windows: Download from https://github.com/UB-Mannheim/tesseract/wiki
# macOS: brew install tesseract
# Linux: sudo apt install tesseract-ocr

# 6. Run the tool
python main_demo.py
```

### For Pushing Your Code to GitHub

```bash
# 1. Make changes (download papers, etc.)
python main_demo.py
# ... use options 3 and 4 ...

# 2. Prepare for GitHub
git add .
git status  # Verify .env is NOT shown!

# 3. Commit
git commit -m "Add exam papers and extraction results

- Scraped Computer Science papers
- Extracted questions from PDFs
- Ready for analysis"

# 4. Push
git push origin main

# 5. Verify on GitHub
# - Check that .env is NOT there
# - .env.example should be present
```

---

## Security Checklist Before Uploading to GitHub

- [ ] `.env` file NOT committed (should be in .gitignore)
- [ ] `.env.example` properly copied from `.env.example`
- [ ] No hardcoded API keys in any Python files
- [ ] `requirements.txt` is up to date
- [ ] `README.md` has clear setup instructions
- [ ] `.gitignore` includes `.env`, `__pycache__/`, `venv/`

Run this to verify:
```bash
git status
# should NOT show: .env
# should show: .env.example
```

---

## What Gets Uploaded vs What Doesn't

### ✅ WILL BE UPLOADED TO GITHUB
- All Python source files (.py)
- requirements.txt
- README.md, QUICK_START.md
- .env.example (template)
- .gitignore
- setup.py

### ❌ WON'T BE UPLOADED (protected by .gitignore)
- `.env` (your API keys - dangerous!)
- `backend/ai/agent/data/raw_papers/` (PDFs are large)
- `backend/ai/agent/outputs/` (generated results)
- `backend/ai/agent/logs/` (log files)
- `__pycache__/` (compiled Python)
- `venv/` (virtual environment)

---

## Credentials & API Keys Management

### For Development (Local)
```bash
# Create .env in your local machine
cp .env.example .env
# Edit .env with your actual API keys
# This file is ignored by Git
```

### For GitHub
```bash
# .env.example has placeholders only
OLLAMA_API_URL=http://localhost:11434
MATHPIX_APP_ID=  # Leave empty in example
MATHPIX_APP_KEY= # Leave empty in example
```

### For Collaborators
When someone clones your repo, they:
1. See `.env.example`
2. Create their own `.env` locally
3. Add their own API keys if needed
4. Never commit `.env`

---

## Troubleshooting GitHub Upload

### Issue: "fatal: pathspec '.env' did not match any files"
✓ Good! This means .env is properly ignored.

### Issue: ".env is listed in git status"
```bash
# Add to .gitignore and remove from tracking
echo ".env" >> .gitignore
git rm --cached .env
git commit -m "Remove .env from tracking"
```

### Issue: Large PDF files cause slow push
PDFs should be in `.gitignore` already. Check:
```bash
ls -lh backend/ai/agent/data/raw_papers/
# Should be empty or not exist
```

---

## Example .env File (LOCAL ONLY)

```bash
# This is your LOCAL .env file (NOT in GitHub)
# Edit with your actual credentials

OLLAMA_API_URL=http://localhost:11434
OLLAMA_MODEL=koesn/llama3-8b-instruct:latest

MATHPIX_APP_ID=your_actual_id_here
MATHPIX_APP_KEY=your_actual_key_here

USE_LLM_CLEANING=true
USE_MATHPIX=false
```

**Remember:** This file is NEVER committed to GitHub!

---

## Next Steps

1. ✅ You have all files ready
2. ✅ Download papers with `python main_demo.py`
3. ✅ Extract questions 
4. ✅ Review results in `backend/ai/agent/outputs/`
5. 📤 Push to GitHub using git commands above
6. 🎉 Share your repo!

Happy coding! 🚀
