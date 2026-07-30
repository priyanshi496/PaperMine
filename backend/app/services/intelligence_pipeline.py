import json
from sqlalchemy.orm import Session
from app.db import models
from app.services.financial_utils import (
    clean_amount,
    normalize_gstin,
    normalize_invoice_number,
)

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

    # Normalize GSTIN and invoice_number ONCE, right here, at the single
    # point they enter the system. Every downstream read (vendor matching,
    # duplicate detection, fraud checks, profile-chunk text, SQL lookups)
    # uses this same canonical value, so a whitespace/case difference from
    # OCR can no longer fragment a vendor into two DB rows or cause a
    # duplicate invoice to slip through undetected.
    supplier_gstin = normalize_gstin(get_val("supplier_gstin"))
    invoice_number = normalize_invoice_number(get_val("invoice_number"))
    
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

    total_amount = clean_amount(get_val("total_amount"))
    subtotal = clean_amount(get_val("taxable_value"))
    tax_amount = clean_amount(get_val("tax_amount"))
    
    # Mathematical Consistency Check
    if total_amount is not None and subtotal is not None and tax_amount is not None:
        if abs((subtotal + tax_amount) - total_amount) > 2.0: # Allow small rounding
            risk_score += 5
            db.add(models.InsightAlert(
                document_id=document_id,
                alert_type="Math Error",
                severity="high",
                message=f"Mathematical inconsistency detected.",
                explanation=f"Subtotal (₹{subtotal}) + Tax (₹{tax_amount}) = ₹{subtotal + tax_amount}, but Grand Total is ₹{total_amount}. Potential tampering.",
                confidence_score=100
            ))
    
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
                # Compare as normalized floats, not raw strings — "1000.0"
                # vs "1000" or "1,000.00" would previously read as a fraud
                # signal even though the amount is identical.
                past_amt = clean_amount(past_inv.total_amount)
                if past_amt is None or total_amount is None:
                    if str(past_inv.total_amount) != str(total_amount):
                        is_fraud = True
                        break
                elif abs(past_amt - total_amount) > 0.01:
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
        tax_amount=str(clean_amount(get_val("tax_amount"))) if clean_amount(get_val("tax_amount")) is not None else None,
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
        # Both sides are already normalized (uppercase, whitespace-stripped)
        # via normalize_gstin above, so this comparison no longer fires a
        # false "OCR Confidence" / "Possible Fraud" alert on a pure
        # case/whitespace difference — only on genuinely different GSTINs.
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
        
        if total_amount is not None:
            # Previously: vendor.total_spent += int(amt_float) — this
            # truncated every invoice's paise/decimal portion before
            # accumulating, so vendor.total_spent silently drifted away
            # from a fresh SUM(Invoice.total_amount) over time. Kept as a
            # float now; round only for display, never for storage.
            vendor.total_spent = (vendor.total_spent or 0) + total_amount
        db.commit()

    # 9. Line Items
    table_data = get_val("table")
    line_item_texts = []
    pending_items = []  # (description, amount) pairs awaiting category assignment

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
            # For price spike detection
            if vendor:
                past_items = db.query(models.LineItem).join(models.Invoice).filter(
                    models.Invoice.vendor_id == vendor.id
                ).all()
            else:
                past_items = []
                
            for row in table_data[1:]:
                if len(row) > max(desc_idx, amount_idx):
                    desc = str(row[desc_idx])
                    amt_str = str(row[amount_idx])
                    
                    qty_idx = next((i for i, h in enumerate(headers) if "qty" in h or "quantity" in h), -1)
                    qty = 1.0
                    if qty_idx != -1 and len(row) > qty_idx:
                        try:
                            qty = float(str(row[qty_idx]).replace(',', ''))
                        except:
                            pass
                            
                    amt = clean_amount(amt_str) or 0.0
                    unit_price = amt / qty if qty > 0 else amt
                    
                    # Price spike detection
                    if vendor and unit_price > 0:
                        # Find past identical items
                        similar_past = [it for it in past_items if it.description and it.description.lower() == desc.lower()]
                        if similar_past:
                            # Check for 30%+ spike
                            past_prices = []
                            for p_it in similar_past:
                                p_amt = clean_amount(p_it.amount) or 0.0
                                # simplistic qty assumption for past items (if we didn't store qty, assume 1, though not ideal)
                                # A better check would be against historical unit prices, but this is a good heuristic.
                                past_prices.append(p_amt)
                            
                            avg_past = sum(past_prices) / len(past_prices)
                            if avg_past > 0 and amt > (avg_past * 1.3):
                                db.add(models.InsightAlert(
                                    document_id=document_id,
                                    alert_type="Price Spike",
                                    severity="medium",
                                    message=f"Price spike detected for item: {desc}",
                                    explanation=f"This item was billed at ₹{amt:,.2f}, which is significantly higher than historical average (₹{avg_past:,.2f}).",
                                    confidence_score=85
                                ))

                    pending_items.append(desc)
                    line_item = models.LineItem(
                        invoice_id=invoice.id,
                        description=desc,
                        amount=amt_str,
                        category=None  # filled in below via batch categorization
                    )
                    db.add(line_item)
                    line_item_texts.append(f"{desc}: {amt_str}")
            db.commit()

    # Real categorization instead of hardcoding "Uncategorized" for every
    # item. This is what lets item_spending() run as a deterministic SQL
    # filter on `category` rather than re-deriving a matching ID set via a
    # live LLM call on every user question (the source of inconsistent
    # category-spending answers).
    if pending_items:
        from app.services.llm_service import call_llm_categorize_items
        categories = call_llm_categorize_items(pending_items)
        created_items = (
            db.query(models.LineItem)
            .filter(models.LineItem.invoice_id == invoice.id)
            .order_by(models.LineItem.id.asc())
            .all()
        )
        for item, category in zip(created_items, categories):
            item.category = category or "Uncategorized"
        db.commit()

    # 10. Two-Stage FAISS Embedding
    # Stage 1: Concise Document Profile (used for retrieval — finds the right invoice fast)
    # Stage 2: Full Structured Invoice (used for answer generation — complete item/financial data)
    from app.services.vector_store import knowledge_engine
    
    doc_type = get_val("document_type") or "Invoice"
    vendor_name = vendor.name if vendor else "Unknown"

    # ── Stage 1: Profile Chunk ─────────────────────────────────────────────────
    profile_parts = [
        f"PROFILE | {doc_type} | Invoice No: {invoice_number} | Vendor: {vendor_name}",
        f"Date: {get_val('invoice_date')} | Total: {total_amount}",
        f"Status: {invoice.verification_status or 'pending'} | Risk Score: {invoice.risk_score or 0}",
        f"GSTIN: {supplier_gstin or 'N/A'}",
        f"Category summary: {', '.join(set(t.split(':')[0].strip() for t in line_item_texts)) if line_item_texts else 'No items'}",
    ]
    profile_text = "\n".join(profile_parts)

    knowledge_engine.embed_and_store(
        db=db,
        document_id=document_id,
        vendor_id=vendor.id if vendor else None,
        doc_type=doc_type,
        category="Profile",
        synthesized_text=profile_text
    )

    # ── Stage 2: Full Structured Invoice Chunk ─────────────────────────────────
    items_table = ""
    table_data = get_val("table")
    if table_data and len(table_data) > 1:
        headers = table_data[0]
        items_table = "| " + " | ".join(str(h) for h in headers) + " |\n"
        items_table += "| " + " | ".join(["---"] * len(headers)) + " |\n"
        for row in table_data[1:]:
            items_table += "| " + " | ".join(str(c) for c in row) + " |\n"
    elif line_item_texts:
        items_table = "\n".join(f"- {t}" for t in line_item_texts)
    else:
        items_table = "No line items available."

    full_parts = [
        f"FULL INVOICE | Invoice No: {invoice_number}",
        f"Vendor: {vendor_name}",
        f"Vendor Address: {get_val('supplier_address') or 'N/A'}",
        f"Supplier GSTIN: {supplier_gstin or 'N/A'}",
        f"Buyer: {get_val('buyer_name') or 'N/A'}",
        f"Buyer GSTIN: {normalize_gstin(get_val('buyer_gstin')) or 'N/A'}",
        f"Invoice Date: {get_val('invoice_date') or 'N/A'}",
        f"Document Type: {doc_type}",
        "",
        "### Financial Breakdown",
        f"Taxable Value: {get_val('taxable_value') or 'N/A'}",
        f"Tax Rate: {get_val('tax_rate') or 'N/A'}",
        f"Tax Amount: {get_val('tax_amount') or 'N/A'}",
        f"Grand Total: {total_amount}",
        "",
        "### Purchased Items",
        items_table,
        "",
        "### Payment Details",
        f"Bank Account: {bank_account_number or 'N/A'}",
        f"Signature Present: {get_val('signature_present') or 'N/A'}",
        "",
        "### Risk Information",
        f"Risk Score: {invoice.risk_score or 0}",
        f"Verification Status: {invoice.verification_status or 'pending'}",
    ]
    full_text = "\n".join(full_parts)

    knowledge_engine.embed_and_store(
        db=db,
        document_id=document_id,
        vendor_id=vendor.id if vendor else None,
        doc_type=doc_type,
        category="FullInvoice",
        synthesized_text=full_text
    )