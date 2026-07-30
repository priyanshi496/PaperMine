from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from app.db.database import get_db
from app.db import models
from datetime import datetime, timedelta

router = APIRouter()

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Dict, Any
from app.db.database import get_db
from app.db import models
from app.api.deps import get_current_user
from app.services.financial_utils import clean_amount
import datetime

router = APIRouter()

@router.get("/overview")
def get_dashboard_overview(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Returns 100% dynamic data for the unified dashboard.
    Applies RBAC automatically based on vendor_id.
    """
    vendor_id = current_user.vendor_id if current_user.role == "vendor" else None

    # Base Queries
    invoice_q = db.query(models.Invoice)
    vendor_q = db.query(models.Vendor)
    alert_q = db.query(models.InsightAlert)

    if vendor_id:
        invoice_q = invoice_q.filter(models.Invoice.vendor_id == vendor_id)
        vendor_q = vendor_q.filter(models.Vendor.id == vendor_id)
        alert_q = alert_q.join(models.Invoice, models.Invoice.document_id == models.InsightAlert.document_id).filter(models.Invoice.vendor_id == vendor_id)

    invoices = invoice_q.all()
    vendors = vendor_q.all()
    alerts = alert_q.all()

    # --- KPIs ---
    total_spend = sum((clean_amount(inv.total_amount) or 0) for inv in invoices)
    total_invoices = len(invoices)
    total_vendors = len(vendors)
    
    pending_count = sum(1 for inv in invoices if inv.verification_status == "Vendor Confirmed" or not inv.verification_status)
    high_risk_count = sum(1 for inv in invoices if (inv.risk_score or 0) >= 5)
    
    # Calculate Business Health Score (0-100)
    # Simple heuristic: 100 - (% of high risk * 50) - (% of pending * 20)
    health_score = 100
    if total_invoices > 0:
        risk_penalty = (high_risk_count / total_invoices) * 50
        pending_penalty = (pending_count / total_invoices) * 20
        health_score = max(0, min(100, int(100 - risk_penalty - pending_penalty)))

    kpis = {
        "total_spend": total_spend,
        "invoices": total_invoices,
        "vendors": total_vendors,
        "health_score": health_score,
        "pending": pending_count,
        "high_risk": high_risk_count
    }

    # --- Charts Data ---
    
    # Monthly Spend
    monthly_map = {}
    for inv in invoices:
        if not inv.invoice_date: continue
        # Expecting YYYY-MM-DD
        parts = inv.invoice_date.split("-")
        if len(parts) >= 2:
            month_key = f"{parts[0]}-{parts[1]}"
            monthly_map[month_key] = monthly_map.get(month_key, 0) + (clean_amount(inv.total_amount) or 0)
    
    monthly_spend = [{"month": k, "amount": v} for k, v in sorted(monthly_map.items())]

    # Department Spend
    dept_map = {}
    for inv in invoices:
        dept = inv.department or "Unassigned"
        dept_map[dept] = dept_map.get(dept, 0) + (clean_amount(inv.total_amount) or 0)
    department_spend = [{"name": k, "value": v} for k, v in dept_map.items() if v > 0]

    # Vendor Spend
    vendor_spend_map = {}
    # Fetch vendor names for invoices
    vendor_dict = {v.id: v.name for v in vendors}
    for inv in invoices:
        v_name = vendor_dict.get(inv.vendor_id, "Unknown")
        vendor_spend_map[v_name] = vendor_spend_map.get(v_name, 0) + (clean_amount(inv.total_amount) or 0)
    vendor_spend = [{"name": k, "value": v} for k, v in sorted(vendor_spend_map.items(), key=lambda x: x[1], reverse=True)[:10]]

    # --- Recent Activity (Latest 10 Invoices) ---
    recent_invoices = invoice_q.order_by(models.Invoice.id.desc()).limit(10).all()
    recent_activity = []
    for inv in recent_invoices:
        v_name = vendor_dict.get(inv.vendor_id, "Unknown")
        amt = clean_amount(inv.total_amount) or 0
        recent_activity.append({
            "id": inv.id,
            "invoice_number": inv.invoice_number,
            "vendor_name": v_name,
            "amount": amt,
            "date": inv.invoice_date,
            "status": inv.verification_status,
            "risk_score": inv.risk_score
        })

    # --- AI Insights (Latest 5 Alerts) ---
    latest_alerts = alert_q.order_by(models.InsightAlert.created_at.desc()).limit(5).all()
    insights = []
    for al in latest_alerts:
        insights.append({
            "id": al.id,
            "type": al.alert_type,
            "severity": al.severity,
            "message": al.message,
            "created_at": al.created_at.isoformat() if al.created_at else None
        })

    return {
        "kpis": kpis,
        "monthly_spend": monthly_spend,
        "department_spend": department_spend,
        "vendor_spend": vendor_spend,
        "recent_activity": recent_activity,
        "insights": insights
    }
