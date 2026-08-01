from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db import models
from pydantic import BaseModel
from app.api.deps import get_current_user
from datetime import datetime

router = APIRouter()

class VendorUpdateRequest(BaseModel):
    name: str | None = None
    gstin: str | None = None
    bank_account: str | None = None
    ifsc: str | None = None

@router.get("/")
def list_vendors(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role not in ["finance_team", "admin", "cfo"]:
        raise HTTPException(status_code=403, detail="Forbidden")

    vendors = db.query(models.Vendor).all()
    results = []
    
    for vendor in vendors:
        # Calculate pending amount and count
        pending_invoices = [inv for inv in vendor.invoices if inv.payment_status != "Paid" and inv.verification_status != "Rejected"]
        pending_count = len(pending_invoices)
        
        pending_amount = 0
        for inv in pending_invoices:
            try:
                if inv.total_amount:
                    val = float(inv.total_amount.replace(",", ""))
                    pending_amount += val
            except:
                pass
                
        total_invoices_count = len(vendor.invoices)

        results.append({
            "id": vendor.id,
            "name": vendor.name or "Unnamed Vendor",
            "gstin": vendor.gstin,
            "department": vendor.department or "Unassigned",
            "trust_score": vendor.trust_score,
            "total_spent": vendor.total_spent,
            "pending_amount": pending_amount,
            "pending_count": pending_count,
            "total_invoices_count": total_invoices_count,
            "is_verified": vendor.is_verified == 1,
            "bank_account": vendor.bank_account
        })
        
    return results

@router.get("/{vendor_id}")
def get_vendor(
    vendor_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role not in ["finance_team", "admin", "cfo"]:
        raise HTTPException(status_code=403, detail="Forbidden")

    vendor = db.query(models.Vendor).filter(models.Vendor.id == vendor_id).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
        
    return {
        "id": vendor.id,
        "name": vendor.name or "Unnamed Vendor",
        "gstin": vendor.gstin,
        "department": vendor.department or "Unassigned",
        "trust_score": vendor.trust_score,
        "total_spent": vendor.total_spent,
        "is_verified": vendor.is_verified == 1,
        "bank_account": vendor.bank_account,
        "ifsc": vendor.ifsc,
        "address": vendor.address
    }


@router.put("/{vendor_id}")
def update_master_profile(
    vendor_id: int, 
    req: VendorUpdateRequest, 
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Forbidden: Only admins can update the Master Profile.")

    vendor = db.query(models.Vendor).filter(models.Vendor.id == vendor_id).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    def update_field(field_name, new_val):
        old_val = getattr(vendor, field_name)
        if new_val is not None and old_val != new_val:
            setattr(vendor, field_name, new_val)
            db.add(models.VendorHistory(
                vendor_id=vendor.id,
                field_changed=field_name,
                old_value=str(old_val) if old_val else None,
                new_value=str(new_val),
                changed_by_id=current_user.id
            ))
            return True
        return False

    updated = False
    updated |= update_field('name', req.name)
    updated |= update_field('gstin', req.gstin)
    updated |= update_field('bank_account', req.bank_account)
    updated |= update_field('ifsc', req.ifsc)
    
    if updated:
        vendor.last_updated_at = datetime.utcnow()
        vendor.updated_by_id = current_user.id
        db.commit()

    return {"status": "success", "message": "Master Profile updated and Audit Trail recorded."}
