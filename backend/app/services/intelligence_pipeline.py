import json
from sqlalchemy.orm import Session
from app.db import models

def run_intelligence_pipeline(db: Session, document_id: int, structured: dict):
    """
    Takes the structured extraction output and populates the relational intelligence tables
    (Vendor, Invoice, LineItem) and generates InsightAlerts.
    """
    if not structured:
        return
        
    doc = db.query(models.Document).filter(models.Document.id == document_id).first()
    if not doc:
        return
        
    def get_val(key):
        return structured.get(key, {}).get("value")

    supplier_name = get_val("supplier_name")
    supplier_gstin = get_val("supplier_gstin")
    
    # 1. Fetch User
    user = None
    if doc.uploaded_by_id:
        user = db.query(models.User).filter(models.User.id == doc.uploaded_by_id).first()

    # 2. Vendor Matching / Isolation
    vendor = None
    if user and user.role == "vendor" and user.vendor_id:
        # Strict isolation: use the authenticated user's vendor ID.
        # NEVER create a new vendor or match against GSTIN in this flow.
        vendor = db.query(models.Vendor).filter(models.Vendor.id == user.vendor_id).first()
    else:
        # Admin flow: Resolve vendor from OCR data
        if supplier_gstin:
            vendor = db.query(models.Vendor).filter(models.Vendor.gstin == supplier_gstin).first()
            if not vendor:
                vendor = models.Vendor(name=supplier_name or "Unknown Vendor", gstin=supplier_gstin)
                db.add(vendor)
                db.commit()
                db.refresh(vendor)
        elif supplier_name:
            import difflib
            all_vendors = db.query(models.Vendor).all()
            vendor_names = [v.name for v in all_vendors if v.name]
            
            matches = difflib.get_close_matches(supplier_name, vendor_names, n=1, cutoff=0.8)
            
            if matches:
                vendor = db.query(models.Vendor).filter(models.Vendor.name == matches[0]).first()
            else:
                vendor = models.Vendor(name=supplier_name)
                db.add(vendor)
                db.commit()
                db.refresh(vendor)
    # 2. Extract New Fields for Risk Engine
    bank_account_number = get_val("bank_account_number")
    signature_present = get_val("signature_present")
    
    # Calculate Risk Score (0-10)
    risk_score = 0
    compliance_issues_found = 0
    duplicate_issues_found = 0
    
    # 3. Compliance Checks
    if signature_present is False:
        risk_score += 2
        compliance_issues_found += 1
        db.add(models.InsightAlert(
            document_id=document_id,
            alert_type="Compliance",
            severity="medium",
            message="Invoice is missing a signature.",
            explanation="The OCR system could not detect a physical or digital signature on this document.",
            confidence_score=90
        ))
        
    if not supplier_gstin:
        risk_score += 3
        compliance_issues_found += 1
        db.add(models.InsightAlert(
            document_id=document_id,
            alert_type="Compliance",
            severity="high",
            message="Missing Supplier GSTIN.",
            explanation="No GSTIN was detected. This could lead to tax compliance issues.",
            confidence_score=95
        ))
        
    # 4. Duplicate Detection (File hash already computed at upload)
    fingerprint = doc.fingerprint
        
    invoice_number = get_val("invoice_number")
    total_amount = get_val("total_amount")
    
    if vendor and invoice_number:
        past_invoices = db.query(models.Invoice).filter(
            models.Invoice.vendor_id == vendor.id,
            models.Invoice.invoice_number == invoice_number
        ).all()
        
        if past_invoices:
            # INTERCEPT: Do not create invoice record yet!
            duplicate_invoice = past_invoices[0]
            doc.duplicate_of_invoice_id = duplicate_invoice.id
            
            is_fraud = False
            for past_inv in past_invoices:
                if str(past_inv.total_amount) != str(total_amount):
                    is_fraud = True
                    break
            
            if is_fraud:
                doc.status = "duplicate_fraud"
                db.add(models.InsightAlert(
                    document_id=document_id,
                    alert_type="Fraud",
                    severity="high",
                    message=f"Fraud Alert! Duplicate invoice #{invoice_number} has a different total amount ({total_amount}) than the original.",
                    explanation="This suggests the invoice was edited and re-submitted to steal funds.",
                    confidence_score=98
                ))
            else:
                doc.status = "duplicate_exact"
                db.add(models.InsightAlert(
                    document_id=document_id,
                    alert_type="Duplicate",
                    severity="medium",
                    message=f"Duplicate invoice detected! Invoice #{invoice_number} from vendor '{vendor.name}' was already processed.",
                    explanation="An invoice with the exact same number from the same vendor exists in the system.",
                    confidence_score=100
                ))
                
            db.commit()
            return # Stop execution here, don't create Invoice
            
    # 5. Create Invoice Record
    invoice = models.Invoice(
        document_id=document_id,
        vendor_id=vendor.id if vendor else None,
        invoice_number=invoice_number,
        invoice_date=get_val("invoice_date"),
        due_date=None,
        total_amount=str(total_amount) if total_amount is not None else None,
        tax_amount=str(get_val("tax_amount")) if get_val("tax_amount") is not None else None,
        verification_status="Unverified",
        risk_score=0 # Will update after all checks
    )
    db.add(invoice)
    db.commit()
    db.refresh(invoice)

    # 6. Master Profile Anomalies (Bank Account & GSTIN)
    if vendor and vendor.bank_account and bank_account_number:
        if vendor.bank_account != bank_account_number:
            risk_score += 4
            db.add(models.InsightAlert(
                document_id=document_id,
                alert_type="Fraud",
                severity="high",
                message=f"Vendor bank account changed to {bank_account_number}.",
                explanation=f"This differs from the verified Master Profile bank account ({vendor.bank_account}). Verify before paying.",
                confidence_score=95
            ))
            
    if vendor and vendor.gstin and supplier_gstin:
        if vendor.gstin != supplier_gstin:
            import difflib
            similarity = difflib.SequenceMatcher(None, vendor.gstin, supplier_gstin).ratio()
            
            if similarity > 0.85:
                # Likely OCR Typos
                db.add(models.InsightAlert(
                    document_id=document_id,
                    alert_type="OCR Confidence Issue",
                    severity="low",
                    message=f"OCR GSTIN {supplier_gstin} differs slightly from verified profile.",
                    explanation=f"The verified Master Profile GSTIN is {vendor.gstin}. This is likely a harmless OCR error.",
                    confidence_score=50
                ))
            else:
                # High severity completely different
                risk_score += 4
                db.add(models.InsightAlert(
                    document_id=document_id,
                    alert_type="Possible Fraud",
                    severity="high",
                    message=f"OCR GSTIN {supplier_gstin} is completely different from verified profile.",
                    explanation=f"The verified Master Profile GSTIN is {vendor.gstin}. This invoice might be for a completely different entity.",
                    confidence_score=95
                ))

    # 7. Update Risk Score and Verification Status
    risk_score = min(risk_score, 10) # Cap at 10
    invoice.risk_score = risk_score
    if risk_score >= 5:
        invoice.verification_status = "Needs Manager Approval"
    db.commit()

    # 8. Vendor Trust Score Update
    if vendor:
        vendor.compliance_issues += compliance_issues_found
        vendor.duplicate_invoices += duplicate_issues_found
        
        # Calculate new trust score (starts at 100, drops by 5 per compliance issue, 10 per duplicate)
        new_trust = 100 - (vendor.compliance_issues * 5) - (vendor.duplicate_invoices * 10)
        vendor.trust_score = max(new_trust, 0)
        
        if total_amount:
            try:
                amt_float = float(str(total_amount).replace(",", ""))
                vendor.total_spent += int(amt_float)
            except ValueError:
                pass
        db.commit()

    # 9. Line Items
    table_data = get_val("table")
    line_item_texts = []
    if table_data and len(table_data) > 1:
        headers = [str(h).lower() for h in table_data[0]]
        
        desc_idx = -1
        amount_idx = -1
        
        for idx, h in enumerate(headers):
            if "description" in h or "item" in h or "particulars" in h or "product" in h:
                desc_idx = idx
            if "amount" in h or "total" in h or "value" in h or "price" in h:
                amount_idx = idx
                
        if desc_idx != -1 and amount_idx != -1:
            for row in table_data[1:]:
                if len(row) > max(desc_idx, amount_idx):
                    desc = str(row[desc_idx])
                    amt = str(row[amount_idx])
                    line_item = models.LineItem(
                        invoice_id=invoice.id,
                        description=desc,
                        amount=amt,
                        category="Uncategorized" 
                    )
                    db.add(line_item)
                    line_item_texts.append(f"{desc}: {amt}")
            db.commit()

    # 10. Synthesized Document Representation & FAISS Insertion
    from app.services.vector_store import knowledge_engine
    
    doc_type = get_val("document_type") or "Invoice"
    
    synthesized_parts = [
        f"Document Type: {doc_type}",
        f"Vendor:\n{vendor.name if vendor else 'Unknown'}",
        f"Invoice Number:\n{invoice_number}",
        f"Date:\n{get_val('invoice_date')}",
        f"Total Amount:\n{total_amount}",
        f"Bank Account:\n{bank_account_number}",
        "Items:",
        "\n".join(line_item_texts) if line_item_texts else "None",
        "Raw OCR Snippets:",
        doc.ocr_text[:1000] if doc.ocr_text else ""
    ]
    
    synthesized_text = "\n\n".join(synthesized_parts)
    
    knowledge_engine.embed_and_store(
        db=db,
        document_id=document_id,
        vendor_id=vendor.id if vendor else None,
        doc_type=doc_type,
        category="General",
        synthesized_text=synthesized_text
    )
