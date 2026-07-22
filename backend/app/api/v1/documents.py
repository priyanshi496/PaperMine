import json
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db import models
from app.services.paddle_ocr import process_document

router = APIRouter()

@router.get("/{document_id}")
def get_document(document_id: int, db: Session = Depends(get_db)):
    doc = db.query(models.Document).filter(models.Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Parse tables from JSON
    tables = []
    for tbl in doc.tables:
        tables.append({
            "id": tbl.id,
            "page": tbl.page,
            "rows": json.loads(tbl.json_data),
        })

    return {
        "id": doc.id,
        "filename": doc.filename,
        "status": doc.status,
        "uploaded_at": doc.uploaded_at,
        "ocr_text": doc.ocr_text,
        "corrected_text": doc.corrected_text,
        "summary": doc.summary,
        "extraction_method": doc.extraction_method,
        "tables": tables,
    }


@router.post("/{document_id}/reprocess")
def reprocess_document(document_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Re-trigger OCR processing for a document that errored out."""
    doc = db.query(models.Document).filter(models.Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if doc.status == "processing":
        raise HTTPException(status_code=400, detail="Document is already being processed")

    # Reset state
    doc.status = "uploaded"
    doc.ocr_text = None
    doc.corrected_text = None
    db.commit()

    background_tasks.add_task(process_document, document_id)
    return {"message": "Reprocessing started", "id": document_id}
