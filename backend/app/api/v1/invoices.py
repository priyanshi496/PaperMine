from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db import models
from pydantic import BaseModel
from typing import Optional
from app.api.deps import get_current_user

router = APIRouter()

class InvoiceVerifyRequest(BaseModel):
    vendor_name: str | None = None
    vendor_gstin: str | None = None
    invoice_number: str | None = None
    invoice_date: str | None = None
    total_amount: str | None = None
    tax_amount: str | None = None
    vendor_bank_account: str | None = None
    vendor_ifsc: str | None = None

@router.get("/")
def list_invoices(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(models.Invoice)
    if current_user.role == "vendor" and current_user.vendor_id:
        from sqlalchemy import or_
        query = query.join(models.Document, models.Invoice.document_id == models.Document.id).filter(
            or_(
                models.Invoice.vendor_id == current_user.vendor_id,
                models.Document.uploaded_by_id == current_user.id
            )
        )
    
    invoices = query.order_by(models.Invoice.id.desc()).all()
    return [
        {
            "id": inv.id,
            "document_id": inv.document_id,
            "invoice_number": inv.invoice_number,
            "invoice_date": inv.invoice_date,
            "department": inv.department or "Unassigned",
            "total_amount": inv.total_amount,
            "verification_status": inv.verification_status,
            "payment_status": inv.payment_status or "Pending",
            "risk_score": inv.risk_score or 0,
            "vendor_name": inv.vendor.name if inv.vendor else "Unknown"
        }
        for inv in invoices
    ]

@router.get("/document/{document_id}")
def get_invoice_by_document(
    document_id: int, 
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    invoice = db.query(models.Invoice).filter(models.Invoice.document_id == document_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
        
    if current_user.role == "vendor" and current_user.vendor_id:
        if invoice.document and invoice.document.uploaded_by_id == current_user.id:
            pass
        elif invoice.vendor_id != current_user.vendor_id:
            raise HTTPException(status_code=403, detail="Forbidden")
    
    vendor = invoice.vendor
    
    # Extract raw OCR fallbacks if master profile is empty
    ocr_gstin = ""
    ocr_bank = ""
    if invoice.document and invoice.document.summary:
        import json
        try:
            summary_dict = json.loads(invoice.document.summary)
            ocr_gstin = summary_dict.get("supplier_gstin", {}).get("value") or ""
            ocr_bank = summary_dict.get("bank_account_number", {}).get("value") or ""
        except:
            pass

    # Fetch alerts for the document
    alerts = db.query(models.InsightAlert).filter(models.InsightAlert.document_id == document_id).all()
    alerts_data = [
        {
            "id": a.id,
            "alert_type": a.alert_type,
            "severity": a.severity,
            "message": a.message,
            "explanation": a.explanation,
            "confidence_score": a.confidence_score
        } for a in alerts
    ]

    return {
        "id": invoice.id,
        "vendor_is_verified": vendor.is_verified == 1 if vendor else False,
        "vendor_name": vendor.name if vendor and vendor.name else "",
        "vendor_gstin": vendor.gstin if vendor and vendor.gstin else ocr_gstin,
        "vendor_bank_account": vendor.bank_account if vendor and vendor.bank_account else ocr_bank,
        "vendor_ifsc": vendor.ifsc if vendor and vendor.ifsc else "",
        "vendor_address": vendor.address if vendor and vendor.address else "",
        "invoice_number": invoice.invoice_number or "",
        "invoice_date": invoice.invoice_date or "",
        "total_amount": invoice.total_amount or "",
        "tax_amount": invoice.tax_amount or "",
        "verification_status": invoice.verification_status,
        "line_items": [{"id": li.id, "description": li.description, "amount": li.amount, "category": li.category} for li in invoice.line_items],
        "alerts": alerts_data
    }

@router.put("/{invoice_id}/verify")
def verify_invoice(
    invoice_id: int, 
    req: InvoiceVerifyRequest, 
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    invoice = db.query(models.Invoice).filter(models.Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
        
    if current_user.role == "vendor" and current_user.vendor_id:
        if invoice.document and invoice.document.uploaded_by_id == current_user.id:
            pass
        elif invoice.vendor_id != current_user.vendor_id:
            raise HTTPException(status_code=403, detail="Forbidden")
        
    invoice.invoice_number = req.invoice_number
    invoice.invoice_date = req.invoice_date
    invoice.total_amount = req.total_amount
    invoice.tax_amount = req.tax_amount
    invoice.verification_status = "Verified"
    
    if invoice.vendor and not invoice.vendor.is_verified:
        # First-Time Onboarding: Populate Master Profile and mark as verified
        from datetime import datetime
        
        def update_field(field_name, new_val):
            old_val = getattr(invoice.vendor, field_name)
            if new_val and old_val != new_val:
                setattr(invoice.vendor, field_name, new_val)
                db.add(models.VendorHistory(
                    vendor_id=invoice.vendor.id,
                    field_changed=field_name,
                    old_value=old_val,
                    new_value=new_val,
                    changed_by_id=current_user.id
                ))

        update_field('name', req.vendor_name)
        update_field('gstin', req.vendor_gstin)
        update_field('bank_account', req.vendor_bank_account)
        update_field('ifsc', req.vendor_ifsc)
        
        invoice.vendor.is_verified = 1
        invoice.vendor.last_updated_at = datetime.utcnow()
        invoice.vendor.updated_by_id = current_user.id
        
    db.commit()
    return {"status": "verified"}
