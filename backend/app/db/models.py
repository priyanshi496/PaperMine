from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base

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

    tables = relationship("Table", back_populates="document", cascade="all, delete")


class Table(Base):
    __tablename__ = "tables"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    page = Column(Integer, nullable=False)
    json_data = Column(Text, nullable=False)  # JSON string of rows/cells
    created_at = Column(DateTime, default=datetime.utcnow)

    document = relationship("Document", back_populates="tables")
