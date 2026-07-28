from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db import models
from typing import Optional
from app.api.deps import get_current_user

router = APIRouter()

@router.get("/")
def get_insights(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(models.InsightAlert)
    
    if current_user.role == "vendor" and current_user.vendor_id:
        # Only get alerts for documents that have an invoice belonging to this vendor
        query = query.join(models.Document).join(models.Invoice, models.Document.id == models.Invoice.document_id).filter(models.Invoice.vendor_id == current_user.vendor_id)
        
    alerts = query.order_by(models.InsightAlert.created_at.desc()).all()
    return [{
        "id": a.id, 
        "document_id": a.document_id, 
        "alert_type": a.alert_type, 
        "severity": a.severity, 
        "message": a.message, 
        "resolved": bool(a.resolved), 
        "created_at": a.created_at
    } for a in alerts]

@router.post("/{alert_id}/resolve")
def resolve_insight(alert_id: int, db: Session = Depends(get_db)):
    alert = db.query(models.InsightAlert).filter(models.InsightAlert.id == alert_id).first()
    if alert:
        alert.resolved = 1
        db.commit()
    return {"status": "ok"}
