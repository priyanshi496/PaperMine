import json
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Header
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db import models
from app.services.paddle_ocr import process_document
from typing import Optional
from app.api.deps import get_current_user
import os

router = APIRouter()

@router.get("/{document_id}/file")
def get_document_file(
    document_id: int, 
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    doc = db.query(models.Document).filter(models.Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
        
    if current_user.role == "vendor" and current_user.vendor_id:
        if doc.uploaded_by_id == current_user.id:
            pass
        else:
            has_access = any(inv.vendor_id == current_user.vendor_id for inv in doc.invoices)
            if not has_access and doc.status not in ["uploaded", "processing", "extracting_tables"]:
                raise HTTPException(status_code=403, detail="Forbidden")

    if not os.path.exists(doc.filepath):
        raise HTTPException(status_code=404, detail="File not found on disk")
        
    return FileResponse(doc.filepath)

@router.get("/{document_id}")
def get_document(
    document_id: int, 
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    doc = db.query(models.Document).filter(models.Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    if current_user.role == "vendor" and current_user.vendor_id:
        if doc.uploaded_by_id == current_user.id:
            # Uploader always has access to their own document
            pass
        else:
            is_processing = doc.status in ["uploaded", "processing", "extracting_tables"]
            if is_processing and len(doc.invoices) == 0:
                # Allow access to processing documents that don't have an invoice assigned yet
                pass
            else:
                has_access = any(inv.vendor_id == current_user.vendor_id for inv in doc.invoices)
                if not has_access:
                    raise HTTPException(status_code=403, detail="Forbidden: You do not have access to this document")

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
        "duplicate_of_invoice_id": doc.duplicate_of_invoice_id,
        "fingerprint": doc.fingerprint
    }


from pydantic import BaseModel

class SummaryUpdateRequest(BaseModel):
    summary: str

@router.put("/{document_id}/summary")
def update_document_summary(
    document_id: int, 
    req: SummaryUpdateRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    doc = db.query(models.Document).filter(models.Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
        
    if current_user.role == "vendor" and current_user.vendor_id:
        if doc.uploaded_by_id == current_user.id:
            pass
        else:
            has_access = any(inv.vendor_id == current_user.vendor_id for inv in doc.invoices)
            if not has_access:
                raise HTTPException(status_code=403, detail="Forbidden")

    doc.summary = req.summary
    db.commit()
    return {"status": "success"}

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

@router.post("/{document_id}/scan")
def scan_document(document_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Trigger processing for a document that was intercepted as a duplicate file."""
    doc = db.query(models.Document).filter(models.Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if doc.status != "duplicate_file":
        raise HTTPException(status_code=400, detail="Document is not in duplicate_file state")

    doc.status = "uploaded"
    db.commit()

    background_tasks.add_task(process_document, document_id)
    return {"message": "Scanning started", "id": document_id}

@router.post("/{document_id}/cancel")
def cancel_document(
    document_id: int, 
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    doc = db.query(models.Document).filter(models.Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
        
    if current_user.role == "vendor" and current_user.vendor_id:
        if doc.uploaded_by_id != current_user.id:
            raise HTTPException(status_code=403, detail="Forbidden")
            
    # Delete the document (cascade deletes tables, alerts)
    db.delete(doc)
    db.commit()
    
    # Try deleting the file
    try:
        import os
        if os.path.exists(doc.filepath):
            os.remove(doc.filepath)
    except:
        pass
        
    return {"status": "success", "message": "Upload cancelled and data removed."}

@router.post("/{document_id}/replace-existing")
def replace_existing_invoice_ocr(
    document_id: int, 
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Takes a duplicate document upload, copies its OCR data to the existing invoice's document,
    and deletes the duplicate upload.
    """
    doc = db.query(models.Document).filter(models.Document.id == document_id).first()
    if not doc or not doc.duplicate_of_invoice_id:
        raise HTTPException(status_code=404, detail="Duplicate document not found")
        
    if current_user.role == "vendor" and current_user.vendor_id:
        if doc.uploaded_by_id != current_user.id:
            raise HTTPException(status_code=403, detail="Forbidden")

    existing_invoice = db.query(models.Invoice).filter(models.Invoice.id == doc.duplicate_of_invoice_id).first()
    if not existing_invoice or not existing_invoice.document:
        raise HTTPException(status_code=404, detail="Existing invoice not found")
        
    old_doc = existing_invoice.document
    
    # Copy OCR data from the new duplicate document to the old one
    old_doc.ocr_text = doc.ocr_text
    old_doc.corrected_text = doc.corrected_text
    old_doc.summary = doc.summary
    old_doc.extraction_method = doc.extraction_method
    old_doc.fingerprint = doc.fingerprint
    
    # Delete old tables, copy new tables
    db.query(models.Table).filter(models.Table.document_id == old_doc.id).delete()
    for tbl in doc.tables:
        db.add(models.Table(
            document_id=old_doc.id,
            page=tbl.page,
            json_data=tbl.json_data
        ))
        
    # Mark old invoice as Unverified so user has to verify the new OCR
    existing_invoice.verification_status = "Unverified"
    
    # Delete the new duplicate document
    db.delete(doc)
    db.commit()
    
    # Try deleting the new file since we replaced the extraction but keep the old file 
    # (or vice-versa depending on business logic - keeping old file for now)
    try:
        import os
        if os.path.exists(doc.filepath):
            os.remove(doc.filepath)
    except:
        pass
        
    return {"status": "success", "invoice_id": existing_invoice.id}

@router.post("/{document_id}/force-create-new")
def force_create_new_invoice(
    document_id: int, 
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Bypass duplicate detection and forcibly create a new invoice record for this document.
    """
    doc = db.query(models.Document).filter(models.Document.id == document_id).first()
    if not doc or not doc.status.startswith("duplicate"):
        raise HTTPException(status_code=404, detail="Document not in duplicate state")
        
    if current_user.role == "vendor" and current_user.vendor_id:
        if doc.uploaded_by_id != current_user.id:
            raise HTTPException(status_code=403, detail="Forbidden")
            
    # Manually extract from doc summary
    import json
    summary_dict = {}
    try:
        if doc.summary:
            summary_dict = json.loads(doc.summary)
    except:
        pass
        
    def get_val(key):
        return summary_dict.get(key, {}).get("value")
        
    vendor_id = None
    if current_user.role == "vendor":
        vendor_id = current_user.vendor_id
    
    # Check if we should override total amount due to missing value
    total_amount = get_val("total_amount")
    
    # Create the invoice!
    invoice = models.Invoice(
        document_id=document_id,
        vendor_id=vendor_id,
        invoice_number=get_val("invoice_number"),
        invoice_date=get_val("invoice_date"),
        total_amount=str(total_amount) if total_amount is not None else None,
        tax_amount=str(get_val("tax_amount")) if get_val("tax_amount") is not None else None,
        verification_status="Unverified",
        risk_score=5 # Add base risk score for being a forced duplicate
    )
    
    doc.status = "processed"
    doc.duplicate_of_invoice_id = None
    
    db.add(invoice)
    db.commit()
    db.refresh(invoice)
    
    return {"status": "success", "invoice_id": invoice.id}
