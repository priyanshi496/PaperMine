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
        
    route = intent_data.get("route", "DOCUMENT_SEARCH")
    filters = intent_data.get("filters", {})
    
    # Optional: convert vendor_name string filter to vendor_id
    vendor_id = None
    if filters.get("vendor_name"):
        v_name = filters["vendor_name"]
        vendor = db.query(models.Vendor).filter(models.Vendor.name.ilike(f"%{v_name}%")).first()
        if vendor:
            vendor_id = vendor.id
            filters["vendor_id"] = vendor_id
            
    if route == "DATABASE":
        sql_templates = intent_data.get("sql_templates", [])
            
        if sql_templates:
            answers = []
            sources = []
            for tmpl in sql_templates:
                ans = _execute_sql_template(db, tmpl, filters)
                if ans:
                    answers.append(ans)
                    sources.append({"type": "SQL Database", "description": f"Executed template: {tmpl}"})
            
            return {
                "answer": "\n\n".join(answers) if answers else "I could not compute that from the structured data.",
                "sources": sources
            }
        else:
            route = "DOCUMENT_SEARCH" # fallback if no templates provided
            
    if route == "DOCUMENT_SEARCH":
        # 2. Semantic FAISS Retrieval
        search_query = intent_data.get("search_query") or query
        docs = knowledge_engine.semantic_search(db, search_query, top_k=5, filters=filters)
        
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
        
    elif route == "GENERAL":
        # Direct LLM call with no RAG or DB
        answer = call_llm_rag_answer(query, "No additional context needed. Answer from your general knowledge as PaperMine.", chat_history)
        return {
            "answer": answer,
            "sources": []
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
        q = db.query(models.Invoice).filter(models.Invoice.verification_status.ilike("verified"))
        if vendor_id:
            q = q.filter(models.Invoice.vendor_id == vendor_id)
        count = q.count()
        return f"There are {count} verified invoice(s)."

    elif template == "pending_invoice_count":
        q = db.query(models.Invoice).filter(
            (models.Invoice.verification_status == None) | 
            (~models.Invoice.verification_status.ilike("verified"))
        )
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
    elif template == "item_spending":
        item_name = filters.get("item_name")
        if not item_name:
            return "I need to know which specific item or category you're asking about to calculate spending."
            
        q = db.query(models.LineItem)
        if vendor_id or invoice_number:
            q = q.join(models.Invoice)
            if vendor_id:
                q = q.filter(models.Invoice.vendor_id == vendor_id)
            if invoice_number:
                q = q.filter(models.Invoice.invoice_number == invoice_number)
            
        all_items = q.all()
        if not all_items:
            return "There are no line items in the database to search through."
            
        # Semantic filtering via LLM
        from app.services.llm_service import call_llm_rag_answer
        items_context = "\n".join([f"ID: {it.id} | Name: {it.description}" for it in all_items])
        prompt = (
            f"The user is asking for their spending on '{item_name}'. "
            "Look at the provided items context. Which items logically fall under this category or name? "
            "IMPORTANT: Reply with ONLY a comma-separated list of the numeric IDs (e.g., 1, 4, 5). "
            "Do NOT include the names of the items. If nothing matches, reply with NONE."
        )
        llm_response = call_llm_rag_answer(prompt, items_context, [])
        
        matched_ids = []
        if llm_response and "NONE" not in llm_response.upper():
            import re
            matched_ids = [int(x) for x in re.findall(r'\d+', llm_response)]
            
        if not matched_ids:
            return f"You haven't spent anything on '{item_name}' (or it isn't listed in the indexed invoices)."
            
        total = 0.0
        item_groups = {} # description -> {"total": 0.0, "count": 0}
        
        for item in all_items:
            if item.id in matched_ids:
                try:
                    clean_amt = str(item.amount).replace("₹", "").replace("Rs", "").replace(",", "").strip()
                    val = float(clean_amt)
                    total += val
                    
                    desc = item.description.strip()
                    if desc not in item_groups:
                        item_groups[desc] = {"total": 0.0, "count": 0}
                    item_groups[desc]["total"] += val
                    item_groups[desc]["count"] += 1
                except (ValueError, TypeError):
                    continue
                    
        if not item_groups:
            return f"I found items for '{item_name}', but couldn't parse their monetary amounts."
            
        breakdown = []
        for desc, stats in item_groups.items():
            breakdown.append(f"- {desc}: ₹{stats['total']:,.2f} ({stats['count']} purchase{'s' if stats['count'] > 1 else ''})")
            
        breakdown_str = "\n".join(breakdown)
        return f"### Spending on '{item_name}'\n\n**Total Spent:** ₹{total:,.2f}\n\n**Individual Items:**\n{breakdown_str}"

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

    elif template == "invoice_items":
        if not invoice_number:
            return "Please specify an invoice number to list its items."
        inv = db.query(models.Invoice).filter(models.Invoice.invoice_number == invoice_number).first()
        if not inv:
            return f"No invoice found with number {invoice_number}."
        items = db.query(models.LineItem).filter(models.LineItem.invoice_id == inv.id).all()
        if not items:
            return f"No line items found for invoice {invoice_number}."
        
        breakdown = []
        for item in items:
            amt = float(str(item.amount).replace(",", "").replace("₹", "").replace("Rs", "").strip()) if item.amount else 0.0
            breakdown.append(f"- {item.description}: ₹{amt:,.2f}")
        breakdown_str = "\n".join(breakdown)
        return f"### Items for Invoice {invoice_number}\n\n{breakdown_str}"

    elif template == "invoice_due_date":
        if not invoice_number:
            return "Please specify an invoice number to check its due date."
        inv = db.query(models.Invoice).filter(models.Invoice.invoice_number == invoice_number).first()
        if not inv:
            return f"No invoice found with number {invoice_number}."
        if inv.due_date:
            try:
                # Try to parse string to date object, assuming YYYY-MM-DD
                from datetime import datetime
                due_date_obj = datetime.strptime(inv.due_date, '%Y-%m-%d')
                return f"Invoice {invoice_number} is due on {due_date_obj.strftime('%d %b %Y')}."
            except ValueError:
                return f"Invoice {invoice_number} is due on {inv.due_date}."
        else:
            return f"Invoice {invoice_number} does not have a specified due date."

    return "I understood this was a structured query, but I don't have a template for it yet. Try rephrasing."

