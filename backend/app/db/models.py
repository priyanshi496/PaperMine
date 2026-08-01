from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, default="vendor") # admin, vendor, finance_team, cfo
    vendor_id = Column(Integer, ForeignKey("vendors.id"), nullable=True)
    
    vendor = relationship("Vendor", foreign_keys=[vendor_id], back_populates="users")


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, index=True)
    filepath = Column(String)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String, default="uploaded")
    ocr_text = Column(Text, nullable=True)
    corrected_text = Column(Text, nullable=True)  # LLM-corrected version of ocr_text
    summary = Column(Text, nullable=True)
    extraction_method = Column(String, nullable=True)  # 'direct' | 'ocr'
    uploaded_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    fingerprint = Column(String, nullable=True)
    duplicate_of_invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=True)

    tables = relationship("Table", back_populates="document", cascade="all, delete")
    invoices = relationship("Invoice", back_populates="document", cascade="all, delete", foreign_keys="[Invoice.document_id]")
    alerts = relationship("InsightAlert", back_populates="document", cascade="all, delete")


class Table(Base):
    __tablename__ = "tables"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    page = Column(Integer, nullable=False)
    json_data = Column(Text, nullable=False)  # JSON string of rows/cells
    created_at = Column(DateTime, default=datetime.utcnow)

    document = relationship("Document", back_populates="tables")


class Vendor(Base):
    __tablename__ = "vendors"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    gstin = Column(String, unique=True, index=True, nullable=True)
    bank_account = Column(String, nullable=True)
    ifsc = Column(String, nullable=True)
    address = Column(String, nullable=True)
    department = Column(String, nullable=True) # E.g., IT, HR, Admin, Cafeteria
    
    is_verified = Column(Integer, default=0) # boolean 0 or 1
    last_updated_at = Column(DateTime, default=datetime.utcnow)
    updated_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    trust_score = Column(Integer, default=100)
    avg_payment_days = Column(Integer, nullable=True)
    total_spent = Column(Integer, default=0)
    
    # History tracking for Trust Score
    late_invoices = Column(Integer, default=0)
    duplicate_invoices = Column(Integer, default=0)
    compliance_issues = Column(Integer, default=0)
    
    invoices = relationship("Invoice", back_populates="vendor")
    users = relationship("User", foreign_keys="[User.vendor_id]", back_populates="vendor")
    history = relationship("VendorHistory", foreign_keys="[VendorHistory.vendor_id]", back_populates="vendor", cascade="all, delete")


class VendorHistory(Base):
    __tablename__ = "vendor_history"

    id = Column(Integer, primary_key=True, index=True)
    vendor_id = Column(Integer, ForeignKey("vendors.id"), nullable=False)
    field_changed = Column(String, nullable=False)
    old_value = Column(String, nullable=True)
    new_value = Column(String, nullable=True)
    changed_at = Column(DateTime, default=datetime.utcnow)
    changed_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    vendor = relationship("Vendor", back_populates="history")



class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    vendor_id = Column(Integer, ForeignKey("vendors.id"), nullable=True)
    
    invoice_number = Column(String, index=True, nullable=True)
    invoice_date = Column(String, nullable=True)
    due_date = Column(String, nullable=True)
    
    subtotal = Column(String, nullable=True)
    tax_amount = Column(String, nullable=True)
    total_amount = Column(String, nullable=True)  # Keeping as string initially to allow parsing safety, or float
    
    department = Column(String, nullable=True) # Extracted from vendor or explicitly set
    
    payment_status = Column(String, default="Pending") # Pending, Paid, Overdue
    verification_status = Column(String, default="Unverified") # Unverified, Verified, Disputed, Needs Manager Approval, Approved, Rejected
    risk_score = Column(Integer, default=0) # 0-10
    rejection_reason = Column(Text, nullable=True)
    
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    approved_at = Column(DateTime, nullable=True)
    approved_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    document = relationship("Document", foreign_keys=[document_id], back_populates="invoices")
    vendor = relationship("Vendor", back_populates="invoices")
    line_items = relationship("LineItem", back_populates="invoice", cascade="all, delete")


class LineItem(Base):
    __tablename__ = "line_items"

    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False)
    description = Column(String, nullable=True)
    amount = Column(String, nullable=True)
    category = Column(String, nullable=True) # E.g. Software, Travel, Office
    
    invoice = relationship("Invoice", back_populates="line_items")


class InsightAlert(Base):
    __tablename__ = "insight_alerts"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=True)
    alert_type = Column(String, index=True) # Duplicate, Fraud, Blurry, PriceHike
    severity = Column(String, default="medium") # low, medium, high
    message = Column(Text, nullable=False)
    explanation = Column(Text, nullable=True)
    confidence_score = Column(Integer, nullable=True) # e.g. 0-100
    resolved = Column(Integer, default=0) # boolean 0 or 1
    created_at = Column(DateTime, default=datetime.utcnow)

    document = relationship("Document", back_populates="alerts")


class DocumentChunk(Base):
    """
    Stores document metadata and textual representation for the FAISS vector database.
    The ID of this table maps 1:1 with the FAISS index ID.
    """
    __tablename__ = "document_chunks"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=True)
    vendor_id = Column(Integer, ForeignKey("vendors.id"), nullable=True)
    
    document_type = Column(String, index=True, nullable=True)
    category = Column(String, nullable=True)
    
    chunk_text = Column(Text, nullable=False) # The synthesized document representation text
    created_at = Column(DateTime, default=datetime.utcnow)

    document = relationship("Document")
    vendor = relationship("Vendor")
