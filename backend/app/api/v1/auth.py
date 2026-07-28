from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db import models
from app.core import security
from app.api.deps import get_current_user

router = APIRouter()

@router.post("/login")
def login_for_access_token(db: Session = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()):
    user = db.query(models.User).filter(models.User.email == form_data.username).first()
    if not user or not security.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=security.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        data={"sub": user.email, "role": user.role, "vendor_id": user.vendor_id},
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token, 
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "role": user.role,
            "vendor_id": user.vendor_id
        }
    }

@router.get("/me")
def read_users_me(current_user: models.User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "role": current_user.role,
        "vendor_id": current_user.vendor_id
    }

@router.get("/vendors")
def get_vendors(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    vendors = db.query(models.Vendor).order_by(models.Vendor.name).all()
    return [{"id": v.id, "name": v.name, "gstin": v.gstin} for v in vendors]

from pydantic import BaseModel
class VendorCreate(BaseModel):
    name: str
    gstin: str | None = None

@router.post("/vendors")
def create_vendor(
    vendor: VendorCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
        
    db_vendor = models.Vendor(name=vendor.name, gstin=vendor.gstin)
    db.add(db_vendor)
    db.commit()
    db.refresh(db_vendor)
    
    # Auto-generate user account
    email = f"{vendor.name.lower().replace(' ', '')}@vendor.com"
    db_user = models.User(
        email=email,
        hashed_password=security.get_password_hash("vendor123"),
        role="vendor",
        vendor_id=db_vendor.id
    )
    db.add(db_user)
    db.commit()
    
    return {"id": db_vendor.id, "name": db_vendor.name, "gstin": db_vendor.gstin, "user_email": email}

class SignupRequest(BaseModel):
    email: str
    password: str
    company_name: str

@router.post("/signup")
def signup_vendor(req: SignupRequest, db: Session = Depends(get_db)):
    # Check if user exists
    if db.query(models.User).filter(models.User.email == req.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
        
    # Create vendor
    db_vendor = models.Vendor(name=req.company_name)
    db.add(db_vendor)
    db.commit()
    db.refresh(db_vendor)
    
    # Create user
    db_user = models.User(
        email=req.email,
        hashed_password=security.get_password_hash(req.password),
        role="vendor",
        vendor_id=db_vendor.id
    )
    db.add(db_user)
    db.commit()
    
    return {"status": "success", "message": "Account created successfully"}

@router.delete("/vendors/{vendor_id}")
def delete_vendor(
    vendor_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
        
    vendor = db.query(models.Vendor).filter(models.Vendor.id == vendor_id).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
        
    # User deletion is handled by cascade or explicitly deleting it here
    user = db.query(models.User).filter(models.User.vendor_id == vendor_id).first()
    if user:
        db.delete(user)
        
    db.delete(vendor)
    db.commit()
    return {"status": "deleted"}
