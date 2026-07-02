import datetime
import os
import uuid
from io import BytesIO

import fitz
from docx import Document
from fastapi import FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel

app = FastAPI()

INCOMING_DOCS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "incoming_docs")

# Cybersecurity incident logs scenario: alert reports, SIEM exports, vulnerability scans
CATEGORIES = ["critical_alert", "siem_export", "vulnerability_scan", "incident_ticket", "informational", "other"]

DEPARTMENT_MAP = {
    "critical_alert": "SOC",
    "siem_export": "SOC",
    "vulnerability_scan": "Security Engineering",
    "incident_ticket": "IT Security",
    "informational": "Security Engineering",
}

SENSITIVE_KEYWORDS = [
    "password", "credential", "breach", "exploit", "cve-", "vulnerability",
    "pii", "ssn", "confidential", "leak", "malware", "ransomware",
]


class GeminiResult(BaseModel):
    classification: str
    sentiment: str
    confidence_score: float
    entities: dict


class SensitivityRequest(BaseModel):
    text: str


class DeleteFileRequest(BaseModel):
    filename: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/categories")
def categories():
    return {"categories": CATEGORIES}


@app.post("/sensitivity")
def sensitivity(payload: SensitivityRequest):
    lowered = payload.text.lower()
    level = "confidential" if any(keyword in lowered for keyword in SENSITIVE_KEYWORDS) else "internal"
    return {"sensitivity": level}


ENTITY_FIELDS = ["people", "organizations", "dates", "amounts"]


@app.post("/enrich")
def enrich(data: GeminiResult):
    is_sensitive = data.classification == "critical_alert" or any(
        keyword in str(data.entities).lower() for keyword in SENSITIVE_KEYWORDS
    )
    filled_fields = sum(1 for field in ENTITY_FIELDS if data.entities.get(field))
    completeness = filled_fields / len(ENTITY_FIELDS)
    # Reward richer entity extraction with a small confidence boost, capped at 1.0
    adjusted_confidence = round(min(1.0, data.confidence_score * (0.85 + 0.15 * completeness)), 2)
    return {
        "document_id": str(uuid.uuid4()),
        "department": DEPARTMENT_MAP.get(data.classification, "General"),
        "sensitivity": "confidential" if is_sensitive else "internal",
        "routing_tag": "escalate" if data.classification == "critical_alert" else (
            "needs-review" if adjusted_confidence < 0.7 else "auto-approved"
        ),
        "confidence_score": adjusted_confidence,
        "processed_at": datetime.datetime.utcnow().isoformat(),
    }


@app.post("/delete-file")
def delete_file(payload: DeleteFileRequest):
    safe_name = os.path.basename(payload.filename)
    file_path = os.path.join(INCOMING_DOCS_DIR, safe_name)
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail=f"File not found: {safe_name}")
    os.remove(file_path)
    return {"deleted": safe_name}


@app.post("/extract-docx")
async def extract_docx(file: UploadFile = File(...)):
    content = await file.read()
    document = Document(BytesIO(content))
    text = "\n".join(paragraph.text for paragraph in document.paragraphs)
    return {"extracted_text": text}


@app.post("/extract-pdf")
async def extract_pdf(file: UploadFile = File(...)):
    content = await file.read()
    pdf = fitz.open(stream=content, filetype="pdf")
    text = "\n".join(page.get_text() for page in pdf)
    pdf.close()
    return {"extracted_text": text}
