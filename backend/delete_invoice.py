import os
from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.db import models
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def delete_invoice(invoice_number: str):
    db: Session = SessionLocal()
    try:
        # Find the invoice
        invoices = db.query(models.Invoice).filter(models.Invoice.invoice_number == invoice_number).all()
        if not invoices:
            logger.info(f"No invoice found with number {invoice_number}")
            return
            
        for invoice in invoices:
            logger.info(f"Found invoice ID {invoice.id} for Vendor ID {invoice.vendor_id}")
            
            # Deduct from vendor stats if needed (basic adjustment)
            vendor = db.query(models.Vendor).filter(models.Vendor.id == invoice.vendor_id).first()
            if vendor and invoice.total_amount:
                try:
                    amt = float(str(invoice.total_amount).replace(',', ''))
                    if vendor.total_spent:
                        vendor.total_spent = max(0, vendor.total_spent - amt)
                        logger.info(f"Adjusted vendor total_spent by deducting {amt}")
                except Exception as e:
                    logger.warning(f"Could not adjust vendor spent: {e}")

            document_id = invoice.document_id
            document = db.query(models.Document).filter(models.Document.id == document_id).first()
            
            # Delete associated document chunks (for vector search)
            chunks_deleted = db.query(models.DocumentChunk).filter(models.DocumentChunk.document_id == document_id).delete()
            logger.info(f"Deleted {chunks_deleted} document chunks")
            
            # Since cascades are set on Document for tables, alerts, invoices, we can just delete the document.
            if document:
                filepath = document.filepath
                db.delete(document) # This should cascade to invoice, line_items, tables, alerts IF cascade is set properly on Document.
                logger.info(f"Deleted document ID {document_id} and all cascaded elements.")
                
                # Try to remove the file
                if filepath and os.path.exists(filepath):
                    try:
                        os.remove(filepath)
                        logger.info(f"Deleted file {filepath}")
                    except Exception as e:
                        logger.error(f"Failed to delete file {filepath}: {e}")
            else:
                # Fallback if document doesn't exist
                db.delete(invoice)
                logger.info(f"Deleted invoice ID {invoice.id}")

        db.commit()
        logger.info("Deletion completed successfully.")

    except Exception as e:
        logger.error(f"An error occurred: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    delete_invoice("ONE-2026-4033")
