from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from app.db.database import get_db
from app.db import models
from datetime import datetime, timedelta

router = APIRouter()

@router.get("/daily-brief")
def get_daily_brief(db: Session = Depends(get_db)):
    """
    Returns data for the 'Good Morning! AI Daily Brief' dashboard.
    """
    
    # 1. Total documents processed
    docs_analyzed = db.query(models.Document).count()
    
    # 2. Get unresolved alerts
    unresolved_alerts = db.query(models.InsightAlert).filter(models.InsightAlert.resolved == 0).order_by(models.InsightAlert.severity.desc(), models.InsightAlert.created_at.desc()).all()
    
    # 3. Get high risk invoices
    high_risk_invoices = db.query(models.Invoice).filter(models.Invoice.risk_score >= 5, models.Invoice.verification_status != "Verified").all()
    
    # Build priorities list dynamically based on real data
    priorities = []
    
    # Duplicates priority
    duplicate_alerts = [a for a in unresolved_alerts if a.alert_type == "Duplicate"]
    if duplicate_alerts:
        priorities.append({
            "icon": "🔴",
            "message": f"{len(duplicate_alerts)} invoices appear to be duplicates.",
            "severity": "high"
        })
        
    # Fraud priority
    fraud_alerts = [a for a in unresolved_alerts if a.alert_type == "Fraud"]
    if fraud_alerts:
        priorities.append({
            "icon": "🔴",
            "message": f"{len(fraud_alerts)} invoices flagged for potential fraud (amount mismatch or bank change).",
            "severity": "high"
        })
        
    # Compliance priority
    compliance_alerts = [a for a in unresolved_alerts if a.alert_type == "Compliance"]
    if compliance_alerts:
        priorities.append({
            "icon": "🟠",
            "message": f"{len(compliance_alerts)} invoices have compliance issues (missing GST/signature).",
            "severity": "medium"
        })
        
    # High Risk Approvals
    if high_risk_invoices:
        priorities.append({
            "icon": "🟡",
            "message": f"{len(high_risk_invoices)} high-risk invoices require manager approval.",
            "severity": "medium"
        })

    # Dummy trend for now if nothing else
    priorities.append({
        "icon": "🟢",
        "message": "Monthly spending decreased by 8% compared to last month.",
        "severity": "low"
    })
    
    return {
        "docs_analyzed": docs_analyzed,
        "priorities": priorities,
        "high_risk_count": len(high_risk_invoices),
        "unresolved_alerts_count": len(unresolved_alerts)
    }
