# VIT Exam Paper Processing Tool

A selected collection of features for processing VIT exam papers, including PDF summarization, PowerPoint processing, web scraping, and question extraction.

## Features Included

### 1. PDF Summarization (`backend/ai/pdf_sum.py`)
- Uses LangChain with Ollama for local AI processing
- Supports RAG (Retrieval-Augmented Generation) for question answering
- Works with any PDF document

### 2. PowerPoint Summarization (`backend/ai/ppt_sum.py`)
- Extracts text from PowerPoint presentations
- Similar RAG-based question answering system
- Works with any PPT document

### 3. Web Scraper (`backend/ai/agent/scraper.py`)
- Scrapes exam papers from https://papers.codechefvit.com
- Supports subject-based searching
- Downloads PDF papers to `backend/ai/agent/data/raw_papers/`
- Uses both requests and Playwright for dynamic content

### 4. Question Extractor (`backend/ai/agent/extractor.py`)
- Extracts questions from PDF exam papers
- Robust text cleaning and header/footer removal
- OCR fallback for scanned PDFs
- MathPix support for mathematical content (optional)
- LLM-based text cleaning (optional)

## Installation

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Install Playwright browsers (for web scraping):
```bash
playwright install
```

4. Install Tesseract OCR (for PDF processing):
- **Windows**: Download from https://github.com/UB-Mannheim/tesseract/wiki
- **macOS**: `brew install tesseract`
- **Ubuntu**: `sudo apt install tesseract-ocr`

# Pull required models
ollama pull koesn/llama3-8b-instruct:latest
ollama pull snowflake-arctic-embed
```

## Usage

### 🚀 Quick Start - Interactive Menu (Easiest)

The easiest way to use all features:

```bash
python main_demo.py
```

This opens an interactive menu with all options:
1. **PDF Summarization** - Summarize any PDF
2. **PowerPoint Summarization** - Summarize any PowerPoint
3. **Scrape Papers** - Download exam papers from CodeChef VIT
4. **Extract Questions** - Extract questions from PDFs
5. **Exit**

### 📥 Scrape & Extract Workflow

#### Step 1: Setup Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env if you need Ollama or MathPix features
# (optional - works fine with defaults)
```

#### Step 2: Download Papers (Scraping)

```bash
python main_demo.py
# When prompted, choose option 3: "Scrape Papers from CodeChef VIT"
# Enter subject: "Computer Science"
# Enter topic: (press Enter to skip)
# Enter max papers: 5
```

**Papers will be saved to:** `backend/ai/agent/data/raw_papers/`

Or use command line directly:
```bash
cd backend/ai/agent
python -c "
from scraper import ExamScraper
scraper = ExamScraper()
papers = scraper.scrape_papers(subject='Computer Science', max_papers=5)
print(f'Downloaded {len(papers)} papers')
"
```

#### Step 3: Extract Questions

```bash
python main_demo.py
# When prompted, choose option 4: "Extract Questions from PDFs"
# Enter topic filter: (press Enter to skip)
```

Or use command line directly:
```bash
cd backend/ai/agent
python run_extract_all.py
```

This will:
- Find all PDFs in `data/raw_papers/`
- Extract questions from each PDF
- Save results to `outputs/extracted_questions_all.json`

#### Step 4: View Results

```bash
# View extracted questions
cat backend/ai/agent/outputs/extracted_questions_all.json
```

Results include:
- Question count per paper
- All extracted questions
- Metadata (subject, topic, timestamp)

### 🔧 Advanced Usage

#### Extract with LLM Cleaning (Requires Ollama)

1. Install Ollama: https://ollama.ai
2. Run: `ollama pull koesn/llama3-8b-instruct:latest`
3. Start server: `ollama serve` (in separate terminal)
4. Edit `.env`: Set `USE_LLM_CLEANING=true`
5. Run extraction with LLM enabled

#### Extract with MathPix OCR (For Math Papers)

1. Get API key from https://www.mathpix.com
2. Edit `.env` with:
   ```
   MATHPIX_APP_ID=your_id
   MATHPIX_APP_KEY=your_key
   ```
3. Set `USE_MATHPIX=true` in `.env`

### Individual Feature Usage

#### PDF Summarization
```bash
cd backend/ai
python pdf_sum.py
```
Provide PDF file path (without quotations)

#### PowerPoint Summarization
```bash
cd backend/ai
python ppt_sum.py
```

## Environment Variables

### Setup `.env` File for GitHub

1. **Copy the template:**
   ```bash
   cp .env.example .env
   ```

2. **Edit `.env` with your API keys (if needed):**
   ```bash
   # For Ollama LLM integration
   OLLAMA_API_URL=http://localhost:11434
   OLLAMA_MODEL=koesn/llama3-8b-instruct:latest
   
   # For MathPix OCR (optional)
   MATHPIX_APP_ID=your_api_id
   MATHPIX_APP_KEY=your_api_key
   ```

3. **Important: `.env` is in `.gitignore`**
   - The `.env` file is automatically excluded from Git
   - Only `.env.example` is committed to GitHub
   - Contributors copy `.env.example` to `.env` locally

### Available Configuration Options

See `.env.example` for all available settings including:
- Ollama/LLM configuration
- MathPix API keys
- File paths and directories
- OCR settings
- Debug options

### Directory Structure

```
Lecture_to_notes_selected/
├── backend/
│   ├── ai/
│   │   ├── pdf_sum.py           # PDF summarization
│   │   ├── ppt_sum.py           # PowerPoint summarization
│   │   └── agent/
│   │       ├── scraper.py       # Web scraper for papers
│   │       ├── extractor.py     # Question extractor
│   │       ├── m.py             # Utility functions
│   │       ├── run_extract_all.py # Batch extraction script
│   │       ├── data/
│   │       │   ├── raw_papers/  # Downloaded PDFs
│   │       │   └── cache/
│   │       ├── outputs/         # Extraction results
│   │       └── logs/            # Log files
│   ├── main.py
│   └── routes/
├── main_demo.py         # Main interactive menu
├── requirements.txt     # Python dependencies
├── .env.example        # Environment variables template
└── README.md
```

## Features in Detail

### Web Scraping Capabilities
- **Subject-based search**: Search for papers by subject (use college courses name)
- **Dynamic content handling**: Uses Playwright for JavaScript-heavy pages
- **Download management**: Automatic PDF download with proper naming

### Question Extraction Features

### AI Processing
- **Local processing**: Uses Ollama for privacy and offline capability
- **RAG system**: Retrieval-augmented generation for accurate answers
- **Embedding support**: Vector search for relevant content retrieval


### Debug Mode

The scraper includes debug features:
- Screenshots saved for troubleshooting
- HTML dumps of problematic pages
- Detailed logging of extraction process

## API Usage
