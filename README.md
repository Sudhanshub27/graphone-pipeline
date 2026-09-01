# Graphone Pipeline 🚀

**Graphone Pipeline** is an asynchronous data ingestion and entity extraction system built in Python 3.11+. It features multi-source scraping (supporting static HTTP requests and client-rendered JavaScript via Playwright), resilient LLM-powered extraction with multi-provider fallback chains (Gemini, Groq, DeepSeek), entity deduplication, Google Sheets export, and a FastAPI-backed control dashboard.

---

## 📁 Project Structure

```
graphone-pipeline/
├── src/
│   ├── scrapers/       # Site-specific async scrapers (aiohttp, httpx, Playwright)
│   ├── llm/            # LLM orchestration & fallback chain (Gemini -> Groq -> DeepSeek)
│   ├── resolution/     # Entity resolution and deduplication algorithms
│   ├── schemas/        # Pydantic v2 data models (Startup, Product, ResearchPaper, Job, News)
│   ├── export/         # Google Sheets export integrations
│   └── dashboard/      # FastAPI backend and web control interface
├── config/
│   └── settings.py     # Centralized Pydantic-settings config (API keys, rate limits, concurrency)
├── data/
│   ├── raw/            # Scraped HTML/JSON cache storage
│   └── processed/      # Validated, structured entity output ready for export
├── logs/               # Structured JSON logs output directory
├── tests/              # Pytest unit and integration test suite
├── .env.example        # Environment variable template
├── architecture.pdf    # System architecture diagram (PDF format)
├── requirements.txt    # Project Python dependencies
└── README.md           # Project documentation
```

---

## 🛠️ Prerequisites & Installation

### 1. Requirements
* **Python**: `3.11` or higher
* **Virtual Environment**: Recommended (`venv` or `conda`)

### 2. Setup Virtual Environment
```bash
# Clone or navigate to project directory
cd graphone-pipeline

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
# On Linux/macOS:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate
```

### 3. Install Dependencies
```bash
# Upgrade pip
pip install --upgrade pip

# Install project requirements
pip install -r requirements.txt

# Install Playwright browser engines (Chromium)
playwright install chromium
```

---

## ⚙️ Configuration

Copy `.env.example` to `.env` and fill in your API credentials:

```bash
cp .env.example .env
```

### Environment Variables Reference

| Variable | Description | Default |
| :--- | :--- | :--- |
| `GEMINI_API_KEY` | Primary LLM Provider API Key (Google Gemini) | `None` |
| `GROQ_API_KEY` | Secondary LLM Provider API Key (Groq) | `None` |
| `DEEPSEEK_API_KEY` | Fallback LLM Provider API Key (DeepSeek) | `None` |
| `GOOGLE_SHEETS_CREDS` | Path to Google Sheets service account credentials JSON | `None` |
| `MAX_CONCURRENT_SCRAPES` | Maximum parallel scraper worker tasks | `5` |
| `MAX_CONCURRENT_LLM_CALLS` | Maximum parallel LLM extraction API calls | `3` |
| `RATE_LIMIT_PER_MINUTE` | Global HTTP rate limit per minute | `60` |
| `HTTP_TIMEOUT_SECONDS` | HTTP request timeout limit (seconds) | `30` |
| `LOG_LEVEL` | Global logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) | `INFO` |

---

## 📊 Data Schemas (Pydantic v2)

All schemas inherit from `BaseRecord` which standardizes data provenance across all ingested records:

* **Provenance Fields**: `schemaVersion`, `recordType`, `source` (`name`, `url`), `collectedAt`

### Supported Entity Schemas:

1. **`Startup`**: Company name, description, website, founding year, founders, funding stage, total funding, location, categories/tags, employee count.
2. **`Product`**: Product name, tagline, description, URL, maker company, launch date, categories/tags, pricing model, upvotes count.
3. **`ResearchPaper`**: Paper title, authors, abstract, published date, PDF URL, journal/conference, DOI, topics, citations count.
4. **`Job`**: Role title, hiring company, location, job type, salary range, description, requirements list, posted date, application URL.
5. **`News`**: Headline title, summary, full body content, author, publication timestamp, category tags, sentiment score.

---

## 🚦 System Architecture & Components

```
                +-------------------------+
                | Scraper Network Layer   |
                | (aiohttp/httpx/Playwright)|
                +------------+------------+
                             |
                             v
                +-------------------------+
                |  Raw HTML / JSON Cache  |
                |     (data/raw/)         |
                +------------+------------+
                             |
                             v
                +-------------------------+
                |    LLM Orchestrator     |
                | Gemini->Groq->DeepSeek  |
                +------------+------------+
                             |
                             v
                +-------------------------+
                |    Pydantic v2 Schema   |
                |     Validation          |
                +------------+------------+
                             |
                             v
                +-------------------------+
                |   Entity Resolution     |
                |    & Deduplication      |
                +------------+------------+
                             |
            +----------------+----------------+
            |                                 |
            v                                 v
+-----------------------+         +-----------------------+
|  Google Sheets Export |         |   FastAPI Dashboard   |
|   (src/export/)       |         |   (src/dashboard/)    |
+-----------------------+         +-----------------------+
```

---

## 🧪 Running Tests

Run unit tests for data schemas and configuration management using `pytest`:

```bash
pytest tests/ -v
```

---

## 🖥️ Running the Dashboard API

Launch the FastAPI backend server:

```bash
uvicorn src.dashboard.main:app --reload --port 8000
```

Access the interactive API documentation at `http://127.0.0.1:8000/docs`.
