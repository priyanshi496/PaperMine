import os
from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.db import models
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def delete_documents_by_fingerprint(fingerprint: str, filename_like: str):
    db: Session = SessionLocal()
    try:
        # Find the documents by fingerprint or filename
        documents = db.query(models.Document).filter(
            (models.Document.fingerprint == fingerprint) | 
            (models.Document.filename.like(f"%{filename_like}%"))
        ).all()
        
        if not documents:
            logger.info("No documents found with the given fingerprint or filename.")
            return
            
        for document in documents:
            logger.info(f"Deleting document ID {document.id} (Status: {document.status}, File: {document.filename})")
            
            # Delete associated document chunks
            db.query(models.DocumentChunk).filter(models.DocumentChunk.document_id == document.id).delete()
            
            # Check for invoices and deduct from vendor stats if needed
            invoices = db.query(models.Invoice).filter(models.Invoice.document_id == document.id).all()
            for invoice in invoices:
                vendor = db.query(models.Vendor).filter(models.Vendor.id == invoice.vendor_id).first()
                if vendor and invoice.total_amount:
                    try:
                        amt = float(str(invoice.total_amount).replace(',', ''))
                        if vendor.total_spent:
                            vendor.total_spent = max(0, vendor.total_spent - amt)
                    except:
                        pass

            filepath = document.filepath
            db.delete(document) # This should cascade
            
            # Try to remove the file
            if filepath and os.path.exists(filepath):
                try:
                    os.remove(filepath)
                    logger.info(f"Deleted file {filepath}")
                except Exception as e:
                    logger.error(f"Failed to delete file {filepath}: {e}")

        db.commit()
        logger.info("Deletion completed successfully.")

    except Exception as e:
        logger.error(f"An error occurred: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    delete_documents_by_fingerprint("4ce844e5e27746e410aef47e1e5a7b98369d674c70fdc0f5f714cae39ffbba69", "onebiteHapoli")
