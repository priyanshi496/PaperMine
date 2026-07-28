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
