import os
import json
from typing import Optional, Dict, Any, List

# Load environment variables from .env manually to avoid extra dependencies
_env_loaded = False

def load_env_file():
    global _env_loaded
    if _env_loaded:
        return
    # Find .env at backend root
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    env_path = os.path.join(base_dir, ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ[k.strip()] = v.strip().strip('"\'')
    _env_loaded = True

# Lazy-loaded clients
_gemini_client = None
_openai_client = None

def get_llm_client():
    """
    Initializes and returns the appropriate LLM client based on environment variables:
    1. GEMINI_API_KEY -> Uses new google-genai SDK Client
    2. OPENAI_API_KEY -> Uses OpenAI client
    3. OPENROUTER_API_KEY -> Uses OpenAI client configured for OpenRouter
    """
    global _gemini_client, _openai_client
    load_env_file()

    # 1. Google Gemini (New SDK)
    gemini_key = os.environ.get("GEMINI_API_KEY")
    if gemini_key:
        if _gemini_client is None:
            try:
                from google import genai
                _gemini_client = genai.Client(api_key=gemini_key)
            except Exception as e:
                print(f"[LLM Service] Gemini (New SDK) init error: {e}")
        if _gemini_client:
            return "gemini", _gemini_client

    # 2. OpenAI or OpenRouter
    openai_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("OPENROUTER_API_KEY")
    if openai_key:
        if _openai_client is None:
            try:
                from openai import OpenAI
                base_url = "https://openrouter.ai/api/v1" if os.environ.get("OPENROUTER_API_KEY") else None
                _openai_client = OpenAI(api_key=openai_key, base_url=base_url)
            except Exception as e:
                print(f"[LLM Service] OpenAI init error: {e}")
        if _openai_client:
            return "openai", _openai_client

    return None, None


def call_llm_structured_extraction(ocr_text: str) -> Optional[str]:
    """
    Sends the noisy raw OCR text to the LLM to return a clean structured JSON string
    matching the expected GST invoice fields.

    IMPORTANT: temperature is pinned to 0. The prompt asks the model to make
    judgment calls on ambiguous OCR characters (0 vs O, 1 vs I, etc.) and to
    "reconstruct" garbled text. At non-zero temperature, the SAME document
    can be extracted with a DIFFERENT invoice_number / GSTIN / amount on
    different runs, because that reconstruction is sampled rather than
    deterministic. Since invoice_number and GSTIN are then used as
    effectively-primary-keys for matching, duplicate detection, and vendor
    resolution, non-determinism here silently breaks all of those downstream.
    temperature=0 doesn't remove OCR ambiguity, but it makes the model's
    resolution of that ambiguity repeatable.
    """
    provider, client = get_llm_client()
    if not provider or not client:
        return None

    prompt = f"""
Analyze this noisy OCR text from an invoice/receipt. Extract the key summary fields and the line-items table.

Please scan the document for the following important fields, looking for any of the listed English or multilingual synonyms. Normalize them to the standard JSON keys listed below:

1. "supplier_name": Supplier/Vendor name, issuer, shop name, merchant.
2. "supplier_address": Supplier/Vendor address, location. Autocorrect any obvious OCR typos or character misrecognitions in addresses (e.g. 'Benoaluru', 'Benoaturu', or 'Bentaluru' should be corrected to 'Bengaluru').
3. "supplier_gstin": Supplier GSTIN, Tax ID, Tax Registration Number, VAT ID, business ID.
4. "invoice_number": Invoice number, bill number, receipt number, doc ref (max 16 chars, letters/numbers/hyphens/slashes only).
5. "invoice_date": Invoice date, bill date, date of issue, transaction date (format: YYYY-MM-DD or DD/MM/YYYY).
6. "buyer_name": Buyer/Customer name, bill to, recipient.
7. "buyer_address": Buyer address.
8. "buyer_gstin": Buyer GSTIN, customer Tax ID/VAT.
9. "place_of_supply": Place of supply (delivery state/location determining intra-state vs inter-state tax).
10. "hsn_sac": HSN/SAC code (classification code for goods/services).
11. "taxable_value": Taxable amount, subtotal, pre-tax value, net amount.
12. "tax_rate": Tax rate (CGST/SGST or IGST rate %, VAT %, sales tax rate).
13. "tax_amount": CGST/SGST amount, IGST amount, VAT amount, total tax amount.
14. "total_amount": Grand total, total invoice value, total amount to pay, gross amount.
15. "signature_present": Signature present (physical or digital / stamp) — return true/false or null.
16. "reverse_charge": Reverse charge applicability (Y/N, true/false, or null).
17. "shipping_address": Shipping address, delivery address (if different from billing address).
18. "transit_ref": Delivery challan, e-way bill reference, consignment note, tracking ref.
19. "bank_account_number": Supplier bank account number, IBAN, or account details.

If any field is not found in the text, return null for its value. If any other key summary fields are present (e.g. order_id, table_number, pay_mode, tip, service charge, phone_number), extract them as key-value pairs at the root level of the JSON using descriptive snake_case keys.

Table Extraction:
Extract the line-items table as a 2D matrix under the "table" key. The first list should contain the exact column headers found (e.g. ["Item", "Qty", "Rate", "Total"]). Subsequent lists should contain the corresponding row values.

Crucial Table Guidelines:
1. Fix any line wrapping or column alignment errors.
2. Autocorrect Gibberish/Garbled Text: OCR engines sometimes misrecognize letters, noise, or paper folds, producing gibberish words. Use context clues, nearby product lines, common industry terminology, and general catalog knowledge to reconstruct the correct names.
3. Mathematical Consistency:
   - For every row, ensure `Rate * Qty = Amount` (within rounding).
   - For the whole table, the sum of all item row `Amount` values must equal the invoice's Grand Total / `total_amount`.
   - Concatenation Check: OCR engines often merge the quantity digit with the amount (e.g. reading '6 16314.00' as '616314.00' or '2 1470.00' as '21470.00'). Detect these anomalies using the Grand Total sum constraint and split them back into their correct separate columns so that all math constraints align.

OCR Confidence Metadata:
Some text segments in the OCR output below are prefixed with [LOW_CONFIDENCE]. These are segments where the OCR engine had very low recognition confidence or where automated analysis detected likely gibberish patterns (e.g. excessive character repetition, non-English character sequences). For these segments:
- Use surrounding context, common product/item names, and invoice structure to reconstruct the correct text.
- Pay special attention to table cells marked [LOW_CONFIDENCE] — the column position is usually correct even if the text is garbled.
- Common OCR substitution errors include: 0↔O, 1↔l↔I, 5↔S, 8↔B, rn→m. Some of these have already been auto-corrected but others may remain.

Expected JSON Structure:
{{
  "supplier_name": "string or null",
  "supplier_address": "string or null",
  "supplier_gstin": "string or null",
  "invoice_number": "string or null",
  "invoice_date": "string or null",
  "buyer_name": "string or null",
  "buyer_address": "string or null",
  "buyer_gstin": "string or null",
  "place_of_supply": "string or null",
  "hsn_sac": "string or null",
  "taxable_value": number or null,
  "tax_rate": "string or number or null",
  "tax_amount": number or null,
  "total_amount": number or null,
  "signature_present": boolean or null,
  "reverse_charge": boolean or null,
  "shipping_address": "string or null",
  "transit_ref": "string or null",
  "bank_account_number": "string or null",
  ... (any other key summary fields present in the text) ...,
  "table": [
    ["Column 1 Header", "Column 2 Header", ...],
    ["Row 1 Cell 1", "Row 1 Cell 2", ...],
    ["Row 2 Cell 1", "Row 2 Cell 2", ...]
  ]
}}

Noisy OCR Text:
{ocr_text}

Return ONLY the raw JSON block. No markdown explanation.
"""

    try:
        if provider == "gemini":
            try:
                from google.genai import types
                config = types.GenerateContentConfig(temperature=0)
            except Exception:
                config = {"temperature": 0}
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=config
            )
            return response.text.strip()
        elif provider == "openai":
            model = os.environ.get("LLM_MODEL", "gpt-4o-mini" if not os.environ.get("OPENROUTER_API_KEY") else "google/gemini-2.5-flash")
            response = client.chat.completions.create(
                model=model,
                temperature=0,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"[LLM Service] Structured extraction failed: {e}")
    return None


def call_llm_categorize_items(descriptions: List[str]) -> List[str]:
    """
    Batch-categorizes line-item descriptions into a small fixed taxonomy at
    INGESTION time (once per invoice), so that spending-by-category queries
    ("how much did I spend on coffee") become a deterministic SQL filter
    instead of a live, non-deterministic LLM ID-matching call made fresh on
    every user question. Runs once, cached in the DB — cheaper and stable.

    Returns a list of category strings in the SAME order as `descriptions`.
    Falls back to "Uncategorized" for every item if the LLM call fails, so
    callers never get a length mismatch.
    """
    fallback = ["Uncategorized"] * len(descriptions)
    if not descriptions:
        return []

    provider, client = get_llm_client()
    if not provider or not client:
        return fallback

    numbered = "\n".join(f"{i}: {d}" for i, d in enumerate(descriptions))
    prompt = f"""Categorize each of the following invoice line items into ONE short, consistent
category label (e.g. "Beverages", "Snacks", "Bakery", "Main Course", "Software",
"Office Supplies", "Travel", "Utilities", "Professional Services", "Other").

Use the SAME category label every time for the same type of item across calls —
consistency matters more than granularity. Prefer coarse, reusable categories
over overly specific ones.

Items (index: description):
{numbered}

Return ONLY a JSON object mapping each index (as a string) to its category label,
no markdown, no explanation. Example: {{"0": "Beverages", "1": "Snacks"}}"""

    try:
        raw = None
        if provider == "gemini":
            try:
                from google.genai import types
                config = types.GenerateContentConfig(temperature=0)
            except Exception:
                config = {"temperature": 0}
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=config
            )
            raw = response.text.strip().removeprefix("```json").removesuffix("```").strip()
        elif provider == "openai":
            model_name = os.environ.get("LLM_MODEL", "gpt-4o-mini")
            response = client.chat.completions.create(
                model=model_name,
                temperature=0,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            raw = response.choices[0].message.content.strip()

        if not raw:
            return fallback

        mapping = json.loads(raw)
        return [mapping.get(str(i), "Uncategorized") for i in range(len(descriptions))]
    except Exception as e:
        print(f"[LLM Service] Categorization failed: {e}")
        return fallback


def call_llm_assistant_intent(query: str, chat_history: list = None) -> Optional[dict]:
    """
    Classifies a user query into STRUCTURED (SQL) or SEMANTIC (RAG).
    Uses Ollama (Qwen3:8B) as primary — free, local, zero latency.
    Falls back to Gemini/OpenAI if Ollama is unavailable.

    NOTE on accuracy: routing correctness gates everything downstream — a
    misrouted aggregate question can't be fixed by anything later in the
    pipeline. An 8B local model is materially weaker at precise multi-class
    JSON routing than Gemini 2.5 Flash / GPT-4o-mini. If you're still seeing
    routing errors after this patch, log which backend actually answered
    each request (see the calling code in assistant.py) and compare
    accuracy — you may want to make the stronger model primary for THIS
    call specifically, even if Ollama stays primary for RAG generation.
    """
    load_env_file()

    # Widened from 2 to 6 turns to match call_llm_rag_answer's window, so
    # pronoun/filter resolution ("what about that invoice?", "which one")
    # has the same amount of context available in both calls.
    history_str = ""
    if chat_history:
        history_str = "--- PREVIOUS CONVERSATION CONTEXT ---\n" + "\n".join(
            [f"{msg.get('role', 'user')}: {msg.get('content', '')}" for msg in chat_history[-6:]]
        ) + "\n-------------------------------------\n\n"

    prompt_text = f"""{history_str}--- CURRENT USER QUESTION ---
"{query}"
-----------------------------

## Three-Tier Routing Architecture

You must classify the user's query into exactly one of these three routes:

### 1. DATABASE
Use this for math, exact counts, aggregations, or querying structured status across all documents.
- The question asks for a pure aggregate number or total across invoices.
- Keywords: count, how many, total spending, average amount, highest invoice, lowest invoice, latest invoice, oldest invoice, pending count, verified count, duplicate count, high-risk count
- The question asks "how much did I spend on [item]?" (e.g., "how much did I spend on coffee")
- The question asks to LIST items, expenses, or line items from the database (e.g., "individual prices with names", "list the items I bought") -> *We use DATABASE so we can query the items without RAG hallucinating math*.

### 2. DOCUMENT_SEARCH
Use this ONLY for reading textual information, summarizing, or finding specific terms within the documents.
- The question asks about document text content: payment terms, bank details, addresses, vendor contacts, signatures.
- The question asks to summarize a specific invoice by number.
- The question asks why a specific document was flagged.

### 3. GENERAL
Use this for conversational chit-chat, greetings, or general financial knowledge that DOES NOT require looking up the user's invoices.
- Examples: "Hi", "Hello", "What is GST?", "How does an invoice work?"
- If the question is conversational or unclear, use GENERAL.

## Query Plan (Only if route == DATABASE)
If DATABASE, you must emit a `query_plan` object instead of generating raw SQL. The executor safely processes this plan.
Schema:
{{
  "type": "aggregate" | "list",
  "entity": "invoice" | "line_item" | "alert",
  "filters": [
      {{"field": "total_amount", "op": ">", "value": 1800}},
      {{"field": "line_item.description", "op": "contains", "value": "coffee"}}
  ],
  "aggregate_fn": "sum" | "avg" | "count" | "min" | "max" | null,
  "aggregate_field": "total_amount" | "amount" | null,
  "group_by": "description" | null,
  "sort_field": "total_amount" | null,
  "sort_dir": "asc" | "desc" | null,
  "limit": 1-50 | null,
  "include_items": true | false
}}

Supported Entities & Fields:
- invoice: vendor_id, risk_score, verification_status, invoice_number, invoice_date, total_amount, tax_amount, line_item.description, line_item.category
- line_item: description, category, amount
- alert: alert_type, severity
Supported Operators (op): >, <, >=, <=, ==, !=, contains

## Filters (Top-level)
Extract any metadata filters if explicitly mentioned IN THE CURRENT QUESTION (e.g. `vendor_name`, `invoice_number`). These act as global scopes outside the query plan.
Do NOT carry over filters from the Previous Conversation unless explicitly referred to.

Return a JSON object ONLY (no markdown, no explanation):
{{"route": "DATABASE" | "DOCUMENT_SEARCH" | "GENERAL", "query_plan": {{...}} | null, "filters": {{"vendor_name": null, "invoice_number": null, "document_type": null, "item_name": null}}, "search_query": "Optimized semantic search string for FAISS or null"}}"""

    # --- Try Ollama first (local, free) ---
    from app.services.ollama_client import ollama_generate, ollama_is_available
    if ollama_is_available():
        system = (
            "You are a precise query router for a financial AI assistant. "
            "Your ONLY job is to output a single valid JSON object with no extra text, "
            "no thinking, no markdown fences."
        )
        try:
            raw = ollama_generate(prompt_text, system=system, temperature=0.0)
            if raw:
                # Strip <think>...</think> blocks that Qwen3 may emit
                import re
                raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
                # Extract the first JSON object in the response
                match = re.search(r"\{.*\}", raw, re.DOTALL)
                if match:
                    parsed = json.loads(match.group())
                    parsed["_backend"] = "ollama"
                    return parsed
        except Exception as e:
            print(f"[OllamaIntent] Error: {e}")

    # --- Fallback: Gemini / OpenAI ---
    provider, client = get_llm_client()
    if not provider or not client:
        return {"route": "DOCUMENT_SEARCH", "sql_templates": [], "filters": {}, "search_query": "", "_backend": "none"}
    try:
        if provider == "gemini":
            try:
                from google.genai import types
                config = types.GenerateContentConfig(temperature=0)
            except Exception:
                config = {"temperature": 0}
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt_text,
                config=config
            )
            raw = response.text.strip().removeprefix("```json").removesuffix("```").strip()
            parsed = json.loads(raw)
            parsed["_backend"] = "gemini"
            return parsed
        elif provider == "openai":
            model_name = os.environ.get("LLM_MODEL", "gpt-4o-mini")
            response = client.chat.completions.create(
                model=model_name,
                temperature=0,
                messages=[{"role": "user", "content": prompt_text}],
                response_format={"type": "json_object"}
            )
            parsed = json.loads(response.choices[0].message.content.strip())
            parsed["_backend"] = "openai"
            return parsed
    except Exception as e:
        print(f"[LLM Service] Assistant intent classification failed: {e}")

    return {"route": "DOCUMENT_SEARCH", "sql_templates": [], "filters": {}, "search_query": "", "_backend": "error_fallback"}

def call_llm_rag_answer(query: str, context: str, chat_history: list = None) -> Optional[str]:
    """
    Generates a final RAG answer using retrieved document chunks as context.
    Uses Ollama (Qwen3:8B) as primary — free, local.
    Falls back to Gemini/OpenAI if Ollama is unavailable.
    """
    load_env_file()

    history_messages = []
    if chat_history:
        for msg in chat_history[-6:]:
            role = msg.get("role", "user")
            if role in ("user", "assistant"):
                history_messages.append({"role": role, "content": msg["content"]})

    system = """# SYSTEM ROLE
You are PaperMine AI, an enterprise-grade Financial Intelligence Assistant.
You are NOT a generic chatbot. You are an AI Finance Analyst helping businesses understand invoices, vendors, expenses, fraud risks and financial documents.
You must always answer professionally, accurately and with evidence. Never hallucinate.
If information is unavailable, explicitly say so.

# RESPONSE STYLE
- Always use markdown formatting
- Use **bold** for important values (amounts, invoice numbers, vendor names)
- Use ## and ### headings to organize sections
- Use bullet points for lists
- Use markdown tables whenever items or comparisons are involved
- Never respond in a single paragraph

# ITEM EXTRACTION RULES
- Extract EVERY line item from the invoice. Never summarize into vague categories like "food items".
- Always include: Item Name | Quantity | Unit Price | Total Amount
- Preserve exact quantities, prices and item names
- If an item appears across multiple invoices, list it under each invoice separately

# INVOICE SUMMARY FORMAT
## Invoice Summary
- **Invoice No:** ...
- **Vendor:** ...
- **Invoice Date:** ...
- **Status:** ...

### Financial Summary
| Component | Amount |
|---|---|
| Subtotal | ₹... |
| **Grand Total** | **₹...** |

### Purchased Items
| Item | Qty | Unit Price | Total |
|---|---|---|---|

### Risk Analysis
- Risk Score: ...
- Duplicate Check: ...
- GST Validation: ...

# MULTIPLE INVOICES: Separate every invoice clearly. Never merge them.

# FRAUD ANALYSIS: Always explain WHY a document is flagged with specific reasons.

# OCR ERRORS: OCR may confuse 1/I/l, 0/O, 5/S. Do not flag as fraud unless difference is significant.

# SOURCES: End every response with **Sources:** listing invoice numbers and document IDs referenced.

# STRICT RULE: Use ONLY information from the provided context chunks.
If the context does not contain the answer, say: "I couldn't find this information in the indexed documents."
Never invent missing values."""

    retrieval_instructions = """**Instructions for using retrieved chunks:**
1. Read ALL chunks before answering. Do not answer from only the first chunk.
2. Merge information from all chunks coherently.
3. If an item appears in multiple invoices, list it under each invoice separately.
4. Extract every line item exactly as written — never omit products.
5. Preserve invoice numbers, quantities, totals and dates exactly.
6. If information conflicts between chunks, mention the conflict.
7. Never invent missing values."""

    user_content = f"""{retrieval_instructions}

## Retrieved Document Chunks
{context}

## User Question
{query}"""

    messages = history_messages + [{"role": "user", "content": user_content}]

    # --- Try Ollama first (local, free) ---
    from app.services.ollama_client import ollama_chat, ollama_is_available
    if ollama_is_available():
        try:
            import re
            raw = ollama_chat(messages, system=system, temperature=0.3)
            if raw:
                # Strip <think>...</think> blocks that Qwen3 may emit in thinking mode
                raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
                return raw
        except Exception as e:
            print(f"[OllamaRAG] Error: {e}")

    # --- Fallback: Gemini / OpenAI ---
    provider, client = get_llm_client()
    if not provider or not client:
        return "I'm sorry, my language model is currently disconnected."

    prompt = f"{system}\n\n{user_content}"
    try:
        if provider == "gemini":
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )
            return response.text.strip()
        elif provider == "openai":
            model_name = os.environ.get("LLM_MODEL", "gpt-4o-mini")
            response = client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Error generating answer: {str(e)}"