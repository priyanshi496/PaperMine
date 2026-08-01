import re
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.db import models
from app.services.llm_service import call_llm_assistant_intent, call_llm_rag_answer
from app.services.vector_store import knowledge_engine
from app.services.financial_utils import (
    clean_amount,
    normalize_invoice_number,
    resolve_invoice_number,
)
from app.services.query_engine import execute_query_plan, format_query_result, QueryPlanError

# Questions that need an LLM to narrate the SQL results, not just dump the raw list.
_INSIGHT_PATTERN = re.compile(
    r"\b(why|trend|reason|explain|analyze|break down|insight|highest|most|report|summary|forecast|predict|compare|health|attention)\b",
    re.IGNORECASE,
)

# Aggregate/quantitative phrasing that should NEVER be answered by RAG, even
# if the intent classifier misroutes it. RAG over a handful of retrieved
# chunks cannot correctly aggregate across documents — a wrong SQL template
# is annoying, a fabricated total from RAG is actively dangerous for a
# financial assistant. This is a deterministic safety net, not a replacement
# for fixing classifier accuracy.
_AGGREGATE_PATTERN = re.compile(
    r"\b(total|how much|how many|count|average|highest|lowest|latest|oldest|"
    r"pending|verified|duplicate|risk)\b",
    re.IGNORECASE,
)


def run_assistant_query(db: Session, query: str, chat_history: list = None, vendor_id: int = None) -> dict:
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

    # --- DETERMINISTIC ROUTING OVERRIDE ---
    query_lower = query.strip().lower()
    last_msg = chat_history[-1]["content"].lower() if chat_history else ""
    was_asked = "would you like me to" in last_msg or "confirm" in last_msg
    was_asked_reason = "please provide a reason for the rejection" in last_msg
    is_confirmation = query_lower in ["yes", "confirm", "approve", "do it", "yes, approve it", "yes, reject it", "reject"]
    is_explicit_cmd = "approve invoice" in query_lower or "reject invoice" in query_lower

    if (was_asked and is_confirmation) or is_explicit_cmd or was_asked_reason:
        route = "WORKFLOW"
        if not intent_data.get("workflow_plan"):
            m = re.search(r'[a-zA-Z]{3}-\d{4}-\d{4}', query)
            target = m.group(0).upper() if m else filters.get("invoice_number")
            if not target and chat_history:
                matches = re.findall(r'[A-Z]{3}-\d{4}-\d{4}', str(chat_history))
                if matches:
                    target = matches[-1]
            intent_data["workflow_plan"] = {
                "action_type": "reject_invoice" if ("reject" in query_lower or was_asked_reason) else "approve_invoice",
                "invoice_number": target
            }
    # --------------------------------------

    # Log which backend actually classified this — lets you compare Ollama
    # vs. the Gemini/OpenAI fallback's routing accuracy empirically instead
    # of guessing. Swap print() for your real logger.
    print(f"[Routing] backend={intent_data.get('_backend')} route={route} "
          f"plan={intent_data.get('query_plan')} query={query!r}")

    # Guardrail: if the classifier says DOCUMENT_SEARCH (or GENERAL) but the
    # question is clearly an aggregate/count/total question with no query
    # plan attached, don't let it fall through to RAG. Re-route to
    # DATABASE with no plan so it hits the "no plan" branch below,
    # which fails loudly with a clear message rather than silently
    # hallucinating a number from retrieved text.
    if route != "DATABASE" and _AGGREGATE_PATTERN.search(query) and not intent_data.get("query_plan"):
        print(f"[Routing] Overriding misrouted aggregate question: {query!r} (was {route})")
        route = "DATABASE"
    
    # Optional: convert vendor_name string filter to vendor_id
    vendor_id = None
    if filters.get("vendor_name"):
        v_name = filters["vendor_name"]
        matches = db.query(models.Vendor).filter(models.Vendor.name.ilike(f"%{v_name}%")).all()
        if len(matches) == 1:
            vendor_id = matches[0].id
            filters["vendor_id"] = vendor_id
        elif len(matches) > 1:
            # Ambiguous — don't silently guess which vendor was meant.
            names = ", ".join(v.name for v in matches)
            return {
                "answer": f"I found multiple vendors matching '{v_name}': {names}. Could you clarify which one you mean?",
                "sources": []
            }
            
    if route == "DATABASE":
        query_plan = intent_data.get("query_plan")
            
        if query_plan:
            # Inject top-level fuzzy invoice resolution into the plan
            invoice_number = filters.get("invoice_number")
            if invoice_number:
                resolved_inv = _resolve_invoice_id(db, invoice_number, vendor_id)
                if resolved_inv:
                    # Guard against LLM emitting a single dict instead of a list
                    if "filters" not in query_plan or not isinstance(query_plan["filters"], list):
                        query_plan["filters"] = [query_plan["filters"]] if isinstance(query_plan.get("filters"), dict) else []
                    
                    query_plan["filters"].append({
                        "field": "invoice_number", "op": "==", "value": resolved_inv.invoice_number
                    })
                else:
                    return {"answer": f"No invoice found with number {invoice_number}.", "sources": []}
            
            try:
                db_result = execute_query_plan(db, query_plan, vendor_id=vendor_id)
                formatted_data = format_query_result(query_plan, db_result)

                # Always feed the raw data to the LLM for a proper narrated answer
                narrated = call_llm_rag_answer(
                    query,
                    f"The SQL database has computed the exact answer to the user's question. Result:\n{formatted_data}\n\nIMPORTANT: Treat this result as the final, correct answer. Do not complain about missing details. Simply formulate this result into a natural, helpful response.",
                    chat_history
                )
                ans = narrated if narrated else formatted_data

                return {
                    "answer": ans,
                    "sources": [{"type": "SQL Database", "description": "Executed Query Plan"}]
                }
            except QueryPlanError as e:
                print(f"[Query Engine] Error executing plan: {e}")
                route = "DOCUMENT_SEARCH"
        else:
            # Previously silently fell through to DOCUMENT_SEARCH here —
            # meaning any DATABASE-routed question the classifier didn't
            # attach a template to would get answered by RAG instead, with
            # no visibility into that happening. Now it's explicit and
            # logged instead of silent.
            print(f"[Routing] DATABASE route with no query plan for query={query!r} — "
                  f"falling back to document search.")
            route = "DOCUMENT_SEARCH"
            
    if route == "DOCUMENT_SEARCH":
        # 2. Semantic FAISS Retrieval
        search_query = intent_data.get("search_query") or query
        # If a specific invoice was resolved (from coreference or explicit mention),
        # prepend the invoice number to the search query to bias FAISS toward the right chunk.
        resolved_invoice = filters.get("invoice_number")
        if resolved_invoice and resolved_invoice not in search_query:
            search_query = f"invoice {resolved_invoice} {search_query}"

        # For broad "all invoices", "compare all", "summarize all" queries expand
        # top_k to retrieve all available chunks so no invoice is missed.
        _ALL_PATTERN = re.compile(r"\b(all|every|each|compare all|summarize all|finance report|monthly report)\b", re.IGNORECASE)
        top_k = 20 if _ALL_PATTERN.search(query) else 5

        # Vendor isolation for RAG
        search_filters = filters.copy()
        if vendor_id:
            search_filters["vendor_id"] = vendor_id
            
        if resolved_invoice:
            inv_obj = _resolve_invoice_id(db, resolved_invoice, vendor_id)
            if inv_obj and inv_obj.document_id:
                search_filters["document_id"] = inv_obj.document_id

        docs = knowledge_engine.semantic_search(db, search_query, top_k=top_k, filters=search_filters)
        
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
        answer = call_llm_rag_answer(query, "No additional context needed.", chat_history, is_general=True)
        return {
            "answer": answer,
            "sources": []
        }


def _resolve_invoice_id(db: Session, raw_invoice_number: str, vendor_id=None):
    """
    Resolves a possibly OCR-noisy user-supplied invoice number to the actual
    stored Invoice row, using normalization + fuzzy matching against what's
    actually in the DB, instead of a fixed O/0 substitution list. Returns
    the Invoice object or None.
    """
    if not raw_invoice_number:
        return None
    q = db.query(models.Invoice)
    if vendor_id:
        q = q.filter(models.Invoice.vendor_id == vendor_id)
    all_invoices = q.all()
    stored_numbers = [inv.invoice_number for inv in all_invoices if inv.invoice_number]

    resolved = resolve_invoice_number(stored_numbers, raw_invoice_number)
    if not resolved:
        return None
    return next((inv for inv in all_invoices if inv.invoice_number == resolved), None)

import json
from app.services.llm_service import call_llm_rag_answer_stream

async def run_assistant_query_stream(db, query, chat_history=None, vendor_id=None, frontend_context=None, user_role=None, user_email=None):
    """
    Streaming version of run_assistant_query. Yields SSE events.
    user_role: "vendor" | "finance_team" | "cfo" | "admin"
    user_email: used to personalize greetings and vendor identification
    """
    intent_data = call_llm_assistant_intent(query, chat_history, frontend_context)
    route = intent_data.get("route", "DOCUMENT_SEARCH")
    filters = intent_data.get("filters", {})
    
    # --- DETERMINISTIC ROUTING OVERRIDE ---
    # Fixes LLM misclassifying "Approve invoice" or "Yes approve it" as DATABASE
    query_lower = query.strip().lower()
    last_msg = chat_history[-1]["content"].lower() if chat_history else ""
    was_asked = "would you like me to" in last_msg or "confirm" in last_msg
    was_asked_reason = "please provide a reason for the rejection" in last_msg
    is_confirmation = query_lower in ["yes", "confirm", "approve", "do it", "yes, approve it", "yes, reject it", "reject"]
    is_explicit_cmd = "approve invoice" in query_lower or "reject invoice" in query_lower

    if (was_asked and is_confirmation) or is_explicit_cmd or was_asked_reason:
        route = "WORKFLOW"
        if not intent_data.get("workflow_plan"):
            m = re.search(r'[a-zA-Z]{3}-\d{4}-\d{4}', query)
            target = m.group(0).upper() if m else filters.get("invoice_number")
            if not target and chat_history:
                matches = re.findall(r'[A-Z]{3}-\d{4}-\d{4}', str(chat_history))
                if matches:
                    target = matches[-1]
            intent_data["workflow_plan"] = {
                "action_type": "reject_invoice" if ("reject" in query_lower or was_asked_reason) else "approve_invoice",
                "invoice_number": target
            }
    # --------------------------------------
    
    _INSIGHT_PATTERN = re.compile(r"\b(why|trend|reason|explain|analyze|break down|insight|highest|most|report|summary|forecast|predict|compare|health|attention)\b", re.IGNORECASE)

    if route == "WORKFLOW":
        workflow_plan = intent_data.get("workflow_plan", {})
        action_type = workflow_plan.get("action_type")
        target_invoice = workflow_plan.get("invoice_number") or filters.get("invoice_number")
        
        if not action_type or not target_invoice:
            yield f"data: {json.dumps({'sources': []})}\n\n"
            yield f"data: {json.dumps({'chunk': 'I could not determine which invoice you want to act on.'})}\n\n"
            return
            
        resolved_inv = _resolve_invoice_id(db, target_invoice, vendor_id)
        if not resolved_inv:
            yield f"data: {json.dumps({'sources': []})}\n\n"
            yield f"data: {json.dumps({'chunk': f'I could not find invoice {target_invoice}.'})}\n\n"
            return

        is_confirmation = query.strip().lower() in ["yes", "confirm", "approve", "do it", "yes, approve it"]
        last_msg = chat_history[-1]["content"].lower() if chat_history else ""
        was_asked = "would you like me to" in last_msg or "confirm" in last_msg
        was_asked_reason = "please provide a reason for the rejection" in last_msg

        if action_type == "reject_invoice":
            if query.strip().lower() in ["no", "cancel", "stop", "abort"]:
                yield f"data: {json.dumps({'sources': []})}\n\n"
                yield f"data: {json.dumps({'chunk': 'Rejection cancelled.'})}\n\n"
                return

            if not was_asked_reason:
                vendor_name = "Unknown"
                if resolved_inv.vendor_id:
                    from app.db import models
                    vendor = db.query(models.Vendor).filter(models.Vendor.id == resolved_inv.vendor_id).first()
                    if vendor:
                        vendor_name = vendor.name
                        
                chunk = f"I found Invoice **{resolved_inv.invoice_number}** from **{vendor_name}** for **₹{resolved_inv.total_amount}**.\n\nWould you like me to reject it? **Please provide a reason for the rejection to confirm.**"
                yield f"data: {json.dumps({'sources': []})}\n\n"
                yield f"data: {json.dumps({'chunk': chunk})}\n\n"
                return
            else:
                resolved_inv.verification_status = "Rejected"
                resolved_inv.rejection_reason = query.strip()
                db.commit()
                yield f"data: {json.dumps({'sources': []})}\n\n"
                yield f"data: {json.dumps({'chunk': f'Invoice {resolved_inv.invoice_number} has been successfully rejected with reason: *{resolved_inv.rejection_reason}*'})}\n\n"
                return

        elif is_confirmation or (was_asked and action_type == "approve_invoice"):
            resolved_inv.verification_status = "Approved"
            db.commit()
            yield f"data: {json.dumps({'sources': []})}\n\n"
            yield f"data: {json.dumps({'chunk': f'Invoice {resolved_inv.invoice_number} has been successfully approved.'})}\n\n"
            return
        else:
            verb = "approve"
            vendor_name = "Unknown"
            if resolved_inv.vendor_id:
                from app.db import models
                vendor = db.query(models.Vendor).filter(models.Vendor.id == resolved_inv.vendor_id).first()
                if vendor:
                    vendor_name = vendor.name
            
            chunk = f"I found Invoice **{resolved_inv.invoice_number}** from **{vendor_name}** for **₹{resolved_inv.total_amount}**.\n\nRisk Score is {resolved_inv.risk_score} and status is {resolved_inv.verification_status}.\n\nWould you like me to **{verb}** it? Please reply 'Yes' to confirm."
            yield f"data: {json.dumps({'sources': []})}\n\n"
            yield f"data: {json.dumps({'chunk': chunk})}\n\n"
            return

    if route == "DATABASE":
        query_plan = intent_data.get("query_plan")
        if query_plan:
            invoice_number = filters.get("invoice_number")
            if invoice_number:
                resolved_inv = _resolve_invoice_id(db, invoice_number, vendor_id)
                if resolved_inv:
                    if "filters" not in query_plan or not isinstance(query_plan["filters"], list):
                        query_plan["filters"] = [query_plan["filters"]] if isinstance(query_plan.get("filters"), dict) else []
                    query_plan["filters"].append({
                        "field": "invoice_number", "op": "==", "value": resolved_inv.invoice_number
                    })
                else:
                    yield f"data: {json.dumps({'sources': []})}\n\n"
                    yield f"data: {json.dumps({'chunk': f'No invoice found with number {invoice_number}.'})}\n\n"
                    return
            try:
                db_result = execute_query_plan(db, query_plan, vendor_id=vendor_id)
                formatted_data = format_query_result(query_plan, db_result)

                if _INSIGHT_PATTERN.search(query):
                    # Also do a quick semantic search to grab business context memos
                    search_filters = {}
                    if vendor_id:
                        search_filters["vendor_id"] = vendor_id
                    docs = knowledge_engine.semantic_search(db, query, top_k=5, filters=search_filters)
                    sources = [{'type': 'SQL Database', 'description': 'Executed Query Plan'}]
                    context_parts = [f"Here is the structured financial data from the database:\n{formatted_data}"]
                    
                    for idx, doc in enumerate(docs):
                        context_parts.append(f"--- Document {idx+1} (ID: {doc['document_id']}) ---\n{doc['text']}")
                        filename = doc.get("filename") or f"Document {doc['document_id']}"
                        is_memo = "BUSINESS CONTEXT DOCUMENT" in doc['text']
                        sources.append({
                            "type": "Business Document" if is_memo else "Invoice",
                            "document_id": doc['document_id'],
                            "filename": filename,
                            "text": doc['text'],
                            "relevance": f"{doc['distance']:.2f}"
                        })
                    
                    yield f"data: {json.dumps({'sources': sources})}\n\n"
                    context = "\n\n".join(context_parts)
                    async for chunk in call_llm_rag_answer_stream(query, context, chat_history, is_general=False, frontend_context=frontend_context, user_role=user_role, user_email=user_email):
                        yield f"data: {json.dumps({'chunk': chunk})}\n\n"
                else:
                    yield f"data: {json.dumps({'sources': [{'type': 'SQL Database', 'description': 'Executed Query Plan'}]})}\n\n"
                    context = f"The SQL database has computed the exact answer to the user's question. Result:\n{formatted_data}\n\nIMPORTANT: Treat this result as the final, correct answer. Do not complain about missing details. Simply formulate this result into a natural, helpful response."
                    async for chunk in call_llm_rag_answer_stream(query, context, chat_history, is_general=False, frontend_context=frontend_context, user_role=user_role, user_email=user_email):
                        yield f"data: {json.dumps({'chunk': chunk})}\n\n"
                return
            except QueryPlanError as e:
                print(f"[QueryPlanError] Falling back to RAG due to: {e}")
                route = "DOCUMENT_SEARCH"
        else:
            route = "DOCUMENT_SEARCH"
            
    if route == "DOCUMENT_SEARCH":
        search_query = intent_data.get("search_query") or query
        resolved_invoice = filters.get("invoice_number")
        if resolved_invoice and resolved_invoice not in search_query:
            search_query = f"invoice {resolved_invoice} {search_query}"
        
        resolved_vendor = filters.get("vendor_name")
        if resolved_vendor and resolved_vendor not in search_query:
            search_query = f"{resolved_vendor} {search_query}"

        _ALL_PATTERN = re.compile(r"\b(all|every|each|compare all|summarize all|finance report|monthly report)\b", re.IGNORECASE)
        top_k = 20 if _ALL_PATTERN.search(query) else 5

        search_filters = filters.copy()
        if vendor_id:
            search_filters["vendor_id"] = vendor_id
            
        if resolved_invoice:
            inv_obj = _resolve_invoice_id(db, resolved_invoice, vendor_id)
            if inv_obj and inv_obj.document_id:
                search_filters["document_id"] = inv_obj.document_id

        docs = knowledge_engine.semantic_search(db, search_query, top_k=top_k, filters=search_filters)
        
        if not docs:
            yield f"data: {json.dumps({'sources': []})}\n\n"
            yield f"data: {json.dumps({'chunk': 'I couldn\'t find any relevant documents in the knowledge base.'})}\n\n"
            return
            
        context_parts = []
        sources = []
        for idx, doc in enumerate(docs):
            context_parts.append(f"--- Document {idx+1} (ID: {doc['document_id']}) ---\n{doc['text']}")
            filename = doc.get("filename") or f"Document {doc['document_id']}"
            is_memo = "BUSINESS CONTEXT DOCUMENT" in doc['text']
            
            sources.append({
                "type": "Business Document" if is_memo else "Invoice",
                "document_id": doc['document_id'],
                "filename": filename,
                "text": doc['text'],
                "relevance": f"{doc['distance']:.2f}"
            })
            
        context = "\n\n".join(context_parts)
        yield f"data: {json.dumps({'sources': sources})}\n\n"
        
        async for chunk in call_llm_rag_answer_stream(query, context, chat_history, is_general=False, frontend_context=frontend_context, user_role=user_role, user_email=user_email):
            yield f"data: {json.dumps({'chunk': chunk})}\n\n"
        return
        
    elif route == "GENERAL":
        yield f"data: {json.dumps({'sources': []})}\n\n"
        async for chunk in call_llm_rag_answer_stream(query, "No additional context needed.", chat_history, is_general=True, frontend_context=frontend_context, user_role=user_role, user_email=user_email):
            yield f"data: {json.dumps({'chunk': chunk})}\n\n"
        return
    return
