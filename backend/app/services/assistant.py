from sqlalchemy.orm import Session
from sqlalchemy import func
from app.db import models
from app.services.llm_service import call_llm_assistant_intent, call_llm_rag_answer
from app.services.vector_store import knowledge_engine

def run_assistant_query(db: Session, query: str, chat_history: list = None) -> dict:
    """
    Main entry point for the Hybrid Assistant.
    """
    if chat_history is None:
        chat_history = []
        
    # 1. Classify Intent (pass history so it can resolve pronouns like "Which ONE")
    intent_data = call_llm_assistant_intent(query, chat_history)
    if not intent_data:
        return {"answer": "Error determining query intent.", "sources": []}
        
    intent = intent_data.get("intent", "SEMANTIC")
    filters = intent_data.get("filters", {})
    
    # Optional: convert vendor_name string filter to vendor_id
    vendor_id = None
    if filters.get("vendor_name"):
        v_name = filters["vendor_name"]
        vendor = db.query(models.Vendor).filter(models.Vendor.name.ilike(f"%{v_name}%")).first()
        if vendor:
            vendor_id = vendor.id
            filters["vendor_id"] = vendor_id
            
    if intent == "STRUCTURED":
        sql_template = intent_data.get("sql_template")
        answer = _execute_sql_template(db, sql_template, filters)
        return {
            "answer": answer,
            "sources": [{"type": "SQL Database", "description": f"Executed template: {sql_template}"}]
        }
    else:
        # 2. Semantic FAISS Retrieval
        docs = knowledge_engine.semantic_search(db, query, top_k=5, filters=filters)
        
        if not docs:
            return {"answer": "I couldn't find any relevant documents in the knowledge base.", "sources": []}
            
        context_parts = []
        sources = []
        
        for idx, doc in enumerate(docs):
            context_parts.append(f"--- Document {idx+1} (ID: {doc['document_id']}) ---\n{doc['text']}")
            sources.append({
                "type": "Document Chunk",
                "document_id": doc['document_id'],
                "relevance": f"{doc['distance']:.2f}"
            })
            
        context = "\n\n".join(context_parts)
        
        # 3. RAG LLM Answer
        answer = call_llm_rag_answer(query, context, chat_history)
        
        return {
            "answer": answer,
            "sources": sources
        }

def _execute_sql_template(db: Session, template: str, filters: dict) -> str:
    """
    Executes a safe predefined SQL template based on intent.
    """
    vendor_id = filters.get("vendor_id")
    invoice_number = filters.get("invoice_number")

    # --- COUNT templates ---
    if template == "count_invoices":
        q = db.query(models.Invoice)
        if vendor_id:
            q = q.filter(models.Invoice.vendor_id == vendor_id)
        count = q.count()
        return f"You have {count} invoice(s) in the system."

    elif template == "verified_invoice_count":
        q = db.query(models.Invoice).filter(models.Invoice.verification_status == "verified")
        if vendor_id:
            q = q.filter(models.Invoice.vendor_id == vendor_id)
        count = q.count()
        return f"There are {count} verified invoice(s)."

    elif template == "pending_invoice_count":
        q = db.query(models.Invoice).filter(models.Invoice.verification_status != "verified")
        if vendor_id:
            q = q.filter(models.Invoice.vendor_id == vendor_id)
        count = q.count()
        return f"There are {count} unverified / pending invoice(s)."

    elif template == "duplicate_count":
        q = db.query(models.InsightAlert).filter(models.InsightAlert.alert_type == "Duplicate")
        count = q.count()
        return f"There are {count} duplicate invoice alert(s) in the system."

    elif template == "high_risk_invoices":
        q = db.query(models.Invoice).filter(models.Invoice.risk_score >= 5)
        if vendor_id:
            q = q.filter(models.Invoice.vendor_id == vendor_id)
        count = q.count()
        return f"There are {count} high-risk invoice(s) that require review."

    # --- AGGREGATION templates ---
    elif template == "total_spending":
        q = db.query(models.Invoice)
        if vendor_id:
            q = q.filter(models.Invoice.vendor_id == vendor_id)
        total = sum(float(inv.total_amount or 0) for inv in q.all())
        return f"Your total spending across all invoices is ₹{total:,.2f}."

    elif template == "average_invoice_amount":
        q = db.query(models.Invoice)
        if vendor_id:
            q = q.filter(models.Invoice.vendor_id == vendor_id)
        invoices = q.all()
        if not invoices:
            return "No invoices found to calculate an average."
        avg = sum(float(inv.total_amount or 0) for inv in invoices) / len(invoices)
        return f"Your average invoice amount is ₹{avg:,.2f}."

    elif template == "highest_invoice_amount":
        q = db.query(models.Invoice)
        if vendor_id:
            q = q.filter(models.Invoice.vendor_id == vendor_id)
        invoices = q.all()
        if not invoices:
            return "No invoices found."
        best = max(invoices, key=lambda inv: float(inv.total_amount or 0))
        return f"Your highest invoice amount is ₹{float(best.total_amount):,.2f} (Invoice No: {best.invoice_number})."

    elif template == "lowest_invoice_amount":
        q = db.query(models.Invoice)
        if vendor_id:
            q = q.filter(models.Invoice.vendor_id == vendor_id)
        invoices = [inv for inv in q.all() if inv.total_amount]
        if not invoices:
            return "No invoices found."
        best = min(invoices, key=lambda inv: float(inv.total_amount or 0))
        return f"Your lowest invoice amount is ₹{float(best.total_amount):,.2f} (Invoice No: {best.invoice_number})."

    # --- DATE templates ---
    elif template == "latest_invoice":
        q = db.query(models.Invoice).order_by(models.Invoice.created_at.desc())
        if vendor_id:
            q = q.filter(models.Invoice.vendor_id == vendor_id)
        inv = q.first()
        if not inv:
            return "No invoices found."
        return f"Your latest invoice is No. {inv.invoice_number} for ₹{float(inv.total_amount or 0):,.2f}, uploaded on {inv.created_at.strftime('%d %b %Y') if inv.created_at else 'unknown date'}."

    elif template == "oldest_invoice":
        q = db.query(models.Invoice).order_by(models.Invoice.created_at.asc())
        if vendor_id:
            q = q.filter(models.Invoice.vendor_id == vendor_id)
        inv = q.first()
        if not inv:
            return "No invoices found."
        return f"Your oldest invoice is No. {inv.invoice_number} for ₹{float(inv.total_amount or 0):,.2f}, uploaded on {inv.created_at.strftime('%d %b %Y') if inv.created_at else 'unknown date'}."

    # --- VENDOR/SPECIFIC templates ---
    elif template == "vendor_spending":
        if not vendor_id:
            return "Please specify a vendor name to look up their spending."
        q = db.query(models.Invoice).filter(models.Invoice.vendor_id == vendor_id)
        total = sum(float(inv.total_amount or 0) for inv in q.all())
        vendor = db.query(models.Vendor).filter(models.Vendor.id == vendor_id).first()
        name = vendor.name if vendor else "that vendor"
        return f"Total spending for {name} is ₹{total:,.2f}."

    elif template == "invoice_by_number":
        if not invoice_number:
            return "Please specify an invoice number to look up."
        inv = db.query(models.Invoice).filter(models.Invoice.invoice_number == invoice_number).first()
        if not inv:
            return f"No invoice found with number {invoice_number}."
        return (
            f"Invoice {inv.invoice_number}: "
            f"Amount ₹{float(inv.total_amount or 0):,.2f}, "
            f"Status: {inv.verification_status or 'pending'}, "
            f"Risk Score: {inv.risk_score or 0}."
        )

    return "I understood this was a structured query, but I don't have a template for it yet. Try rephrasing."

