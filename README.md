# Intelligent Cloud Document Analyst 🤖

An n8n + Google Gemini automation pipeline that watches a Google Drive folder for incoming documents, extracts their text, analyzes them with Gemini AI, enriches the results via a custom FastAPI microservice, and publishes the output to Google Sheets and Gmail.

**Scenario:** Cybersecurity incident logs — alert reports, SIEM exports, vulnerability scans, and incident tickets.

## Architecture

```
Google Drive           n8n (Google Drive     text extraction (PDF/DOCX)
"incoming_docs"    →     Trigger/router)  →
folder                                        │
                                              ▼
                                    Gemini API (summary, classification,
                                    sentiment, entities, action items)
                                              │
                                              ▼
                              Metadata API (FastAPI enrichment)
                                              │
                    ┌─────────────────────────┼─────────────────────────┐
                    ▼                         ▼                         ▼
            Google Sheets          Google Drive "output_docs"        Gmail
           (results database)        (JSON + Markdown)           (notification)
```

## Components

| Component | Description |
|---|---|
| **n8n workflow** (`n8n.json`) | Orchestrates file detection, routing, Gemini calls, enrichment, and output |
| **Metadata API** (`main.py`) | FastAPI microservice for text extraction and enrichment logic |
| **Google Gemini** | LLM used for summarization, classification, sentiment, and entity extraction |
| **Google Sheets** | Cloud results database (one row per processed document) |
| **Gmail** | Sends a notification email when a document finishes processing |

## Metadata API Endpoints

| Endpoint | Description |
|---|---|
| `GET /health` | Health check — returns `{"status": "ok"}` |
| `GET /categories` | Lists available document categories |
| `POST /sensitivity` | Flags text as `confidential` or `internal` based on keyword scan |
| `POST /enrich` | Takes Gemini's output and returns department, sensitivity, routing tag, and adjusted confidence score |
| `POST /extract-pdf` | Extracts text from an uploaded PDF (PyMuPDF) |
| `POST /extract-docx` | Extracts text from an uploaded DOCX (python-docx) |
| `POST /delete-file` | Removes a processed file from the local `incoming_docs/` staging directory |

## Setup

1. **Install dependencies**
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Run the metadata API**
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000 --reload
   ```
   > n8n runs in Docker and reaches this service via `host.docker.internal:8000`, so it must bind to `0.0.0.0` (not just `127.0.0.1`) on port `8000`.

3. **Start n8n (Docker)**
   ```bash
   docker run -d --name n8n --restart unless-stopped -p 5678:5678 \
     -v n8n_data_fresh:/home/node/.n8n \
     n8nio/n8n
   ```
   Then open [http://localhost:5678](http://localhost:5678) in your browser.

4. **Import the n8n workflow**
   - In the n8n UI, import `n8n.json`
   - Configure credentials: Gemini API key (HTTP Header Auth), Google Drive OAuth2, Google Sheets OAuth2, Gmail OAuth2
   - Point the Google Drive Trigger at your `incoming_docs` folder in Google Drive

5. **Drop a document** into the `incoming_docs` folder in Google Drive and watch it flow through Gemini analysis, enrichment, Google Sheets, and email notification.

## Tech Stack

- **AI:** Google Gemini (`gemini-2.5-flash`)
- **Automation:** n8n
- **Microservice:** Python 3.10+, FastAPI, PyMuPDF, python-docx
- **Storage:** Google Drive + Google Sheets API
- **Notifications:** Gmail API (OAuth2)
