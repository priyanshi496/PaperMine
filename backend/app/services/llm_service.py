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

def get_llm_client(purpose: str = "ocr"):
    """
    Initializes and returns the appropriate LLM client based on purpose:
    - "ocr": Prioritizes Gemini
    - "assistant": Prioritizes NVIDIA NIM
    """
    global _gemini_client, _openai_client
    load_env_file()

    # --- Assistant Flow: Prioritize NVIDIA NIM ---
    if purpose == "assistant":
        nvidia_key = os.environ.get("NVIDIA_API_KEY")
        if nvidia_key:
            if _openai_client is None:
                try:
                    from openai import OpenAI
                    _openai_client = OpenAI(
                        base_url="https://integrate.api.nvidia.com/v1",
                        api_key=nvidia_key
                    )
                    os.environ["LLM_MODEL"] = "nvidia/nemotron-3-super-120b-a12b" # Force nemotron-3-super-120b-a12b
                except Exception as e:
                    print(f"[LLM Service] NVIDIA init error: {e}")
            if _openai_client:
                return "openai", _openai_client

    # --- OCR Flow: Prioritize Gemini ---
    if purpose == "ocr":
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

    # --- Fallbacks (if primary for the purpose fails) ---
    
    # 1. Google Gemini (New SDK) - as a fallback for assistant if NVIDIA fails
    gemini_key = os.environ.get("GEMINI_API_KEY")
    if gemini_key and purpose == "assistant":
        if _gemini_client is None:
            try:
                from google import genai
                _gemini_client = genai.Client(api_key=gemini_key)
            except Exception as e:
                pass
        if _gemini_client:
            return "gemini", _gemini_client

    # 2. NVIDIA NIM - as a fallback for OCR if Gemini fails
    nvidia_key = os.environ.get("NVIDIA_API_KEY")
    if nvidia_key and purpose == "ocr":
        if _openai_client is None:
            try:
                from openai import OpenAI
                _openai_client = OpenAI(base_url="https://integrate.api.nvidia.com/v1", api_key=nvidia_key)
                os.environ["LLM_MODEL"] = "nvidia/nemotron-3-super-120b-a12b"
            except Exception as e:
                pass
        if _openai_client:
            return "openai", _openai_client

    # 3. OpenAI or OpenRouter (Generic Fallback)
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
    Extracts structured fields from raw OCR text, prioritizing Gemini.
    """
    if not ocr_text or not ocr_text.strip():
        return None

    provider, client = get_llm_client(purpose="ocr")

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
                model="gemma-4-31b-it",
                contents=prompt,
                config=config
            )
            return response.text.strip()
        elif provider == "openai":
            model = os.environ.get("LLM_MODEL", "gpt-4o-mini" if not os.environ.get("OPENROUTER_API_KEY") else "google/gemma-4-31b-it")
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
    Takes a list of line item descriptions and returns a corresponding list of standard categories.
    """
    fallback = ["Uncategorized"] * len(descriptions)
    if not descriptions:
        return []

    provider, client = get_llm_client(purpose="ocr")
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
                model="gemma-4-31b-it",
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


def call_llm_assistant_intent(query: str, chat_history: list = None, frontend_context: dict = None) -> Optional[dict]:
    """
    Analyzes the user's query and determines the intent, prioritizing NVIDIA NIM.
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

    context_str = ""
    if frontend_context:
        context_str = f"--- FRONTEND CONTEXT ---\nThe user is currently looking at this page on the UI: {json.dumps(frontend_context)}\nUse this to understand vague pronouns like 'this invoice' or 'these vendors'.\n------------------------\n\n"

    prompt_text = f"""{history_str}{context_str}--- CURRENT USER QUESTION ---
"{query}"
-----------------------------

## Three-Tier Routing Architecture

You must classify the user's query into exactly one of these three routes:

### 1. DATABASE
Use for ANY structured data lookup, aggregation, filtering, or counting. This covers:
- **Counts:** "how many invoices", "count of items"
- **Aggregations:** total, sum, average, highest, lowest, min, max spending
- **Filters:** invoices from May, verified invoices, invoices over ₹1500
- **Sorting:** latest invoice, oldest, chronological order, by amount
- **Status checks:** payment_status (Pending/Paid), verification_status (Verified/Unverified)
- **Item/spend lookups:** "how much on coffee", "which invoice has Hot Coffee", "total on sandwiches"
- **Vendor profile:** trust score, GSTIN, total_spent, how many invoices submitted
- **Fraud/alerts:** duplicate invoices, GST mismatches, fraud alerts, risk scores
- **Spending analysis:** purchasing trends, most frequent items, spending by category
- **Hybrid:** verified invoices containing coffee, invoices over ₹1500 with French Fries

### 2. DOCUMENT_SEARCH
Use ONLY for reading rich text that requires the actual invoice document, not structured fields:
- Summarize a specific invoice (needs full text: line items with qty, unit price, GST breakdown)
- Payment terms, bank details, IFSC code, billing address, shipping address
- Supplier or buyer contact information
- Whether invoice is signed or has a stamp
- Explain why an invoice is risky (full fraud context from document)
- Compare two specific invoices in a table (needs both documents)
- Which invoice contains a specific product (if the product text is not in DB)

### 3. GENERAL
Use ONLY for:
- Greetings, chitchat ("Hi", "Thanks", "How are you")
- General financial knowledge NOT tied to uploaded invoices ("What is GST?", "How does an invoice work?")

---

## Query Plan (REQUIRED when route == DATABASE)

Emit a `query_plan` object. The executor safely handles this — you never write SQL.

Schema:
{{
  "type": "aggregate" | "list",
  "entity": "invoice" | "line_item" | "alert" | "vendor",
  "filters": [
      {{"field": "...", "op": "...", "value": "..."}}
  ],
  "aggregate_fn": "sum" | "avg" | "count" | "min" | "max" | null,
  "aggregate_field": "total_amount" | "tax_amount" | "amount" | null,
  "group_by": "description" | "category" | "department" | "vendor_id" | null,
  "sort_field": "total_amount" | "invoice_date" | "tax_amount" | null,
  "sort_dir": "asc" | "desc" | null,
  "limit": integer | null,
  "include_items": true | false
}}

### Supported Entities & Fields:

**entity: invoice**
- invoice_number (text), invoice_date (text, format YYYY-MM-DD), due_date (text)
- payment_status (text: "Pending" means money not yet paid, "Paid" means payment completed)
- verification_status (text: valid values are EXACTLY "Approved", "Rejected", "Vendor Confirmed", "Paid", "Unverified")
  - "Approved" = approved by finance team, ready to pay
  - "Rejected" = rejected by finance team due to fraud/issues
  - "Vendor Confirmed" = submitted by vendor, waiting for finance team review/approval
  - "Paid" = payment completed
  - "Unverified" = newly uploaded, not yet reviewed
  - ⚠️ IMPORTANT: "pending approval" or "awaiting approval" means verification_status == "Vendor Confirmed"
  - ⚠️ IMPORTANT: "pending payment" means payment_status == "Pending"
  - ⚠️ IMPORTANT: "approved invoices" means verification_status == "Approved"
  - ⚠️ IMPORTANT: "rejected invoices" means verification_status == "Rejected"
- risk_score (number 0-10, where >7 is high risk), vendor_id (number), department (text)
- total_amount (amount), tax_amount (amount)
- Cross-filters (only with invoice entity): line_item.description (contains), line_item.category (contains)

**entity: line_item**
- description (text), category (text), amount (amount)

**entity: alert**
- alert_type (text: "Duplicate", "GST Mismatch", "Bank Mismatch"), severity (text: "medium"/"high")

**entity: vendor**
- name (text), gstin (text), trust_score (number), total_spent (number), is_verified (number), duplicate_invoices (number), compliance_issues (number)

Supported Operators (op): >, <, >=, <=, ==, !=, contains

### Routing Examples with Query Plans:

| Question | route | entity | type | filters | agg_fn | sort | include_items |
|---|---|---|---|---|---|---|---|
| How many invoices? | DATABASE | invoice | aggregate | [] | count | null | false |
| List all invoices | DATABASE | invoice | list | [] | null | invoice_date desc | false |
| Invoices from May 2026 | DATABASE | invoice | list | [invoice_date contains "2026-05"] | null | null | false |
| Latest invoice | DATABASE | invoice | list | [] | null | invoice_date desc | false | limit 1 |
| Oldest invoice | DATABASE | invoice | list | [] | null | invoice_date asc | false | limit 1 |
| Total spending | DATABASE | invoice | aggregate | [] | sum | total_amount | null | false |
| Highest invoice | DATABASE | invoice | list | [] | null | total_amount desc | false | limit 1 |
| Unverified invoices | DATABASE | invoice | list | [verification_status == "Unverified"] | null | null | false |
| Pending invoices | DATABASE | invoice | list | [payment_status == "Pending"] | null | null | false |
| Invoices over ₹1500 | DATABASE | invoice | list | [total_amount > 1500] | null | null | false |
| Which invoice has Hot Coffee? | DATABASE | invoice | list | [line_item.description contains "Hot Coffee"] | null | null | true |
| Total spent on coffee | DATABASE | line_item | aggregate | [description contains "coffee"] | sum | amount | null | false |
| Items in invoice 001 | DATABASE | line_item | list | [] | null | null | false | (invoice_number in top-level filters) |
| Most frequent item | DATABASE | line_item | aggregate | [] | count | null | description | false |
| Spending by category | DATABASE | line_item | aggregate | [] | sum | amount | category | false |
| Show all alerts | DATABASE | alert | list | [] | null | null | false |
| Duplicate invoices | DATABASE | alert | list | [alert_type == "Duplicate"] | null | null | false |
| GST mismatch invoices | DATABASE | alert | list | [alert_type == "GST Mismatch"] | null | null | false |
| Bank mismatch invoices | DATABASE | alert | list | [alert_type == "Bank Mismatch"] | null | null | false |
| High risk invoices | DATABASE | invoice | list | [risk_score > 7] | null | null | false |
| Vendor profile | DATABASE | vendor | list | [] | null | null | false |
| My GSTIN | DATABASE | vendor | list | [] | null | null | false |
| Trust score | DATABASE | vendor | list | [] | null | null | false |
| Show approved invoices | DATABASE | invoice | list | [verification_status == "Approved"] | null | null | false |
| Show rejected invoices | DATABASE | invoice | list | [verification_status == "Rejected"] | null | null | false |
| Show invoices pending approval / awaiting approval | DATABASE | invoice | list | [verification_status == "Vendor Confirmed"] | null | null | false |
| Show invoices pending payment | DATABASE | invoice | list | [payment_status == "Pending"] | null | null | false |
| Show paid invoices | DATABASE | invoice | list | [payment_status == "Paid"] | null | null | false |
| Approved invoices with coffee | DATABASE | invoice | list | [verification_status == "Approved", line_item.description contains "coffee"] | null | null | true |
| Invoices >₹1500 with French Fries | DATABASE | invoice | list | [total_amount > 1500, line_item.description contains "French Fries"] | null | null | true |
| Spending trends / most purchased | DATABASE | line_item | aggregate | [] | sum | amount | description | false |
| Highest coffee expense invoice | DATABASE | invoice | list | [line_item.description contains "coffee"] | null | total_amount desc | true | limit 1 |
| Highest GST invoice | DATABASE | invoice | list | [] | null | tax_amount desc | false | limit 1 |
| What taxes were applied? | DATABASE | invoice | list | [] | null | null | false |
| Give me a financial summary of all invoices | DATABASE | invoice | list | [] | null | invoice_date asc | true |
| Compare all invoices | DATABASE | invoice | list | [] | null | invoice_date asc | true |
| Generate a monthly expense report | DATABASE | line_item | aggregate | [] | sum | amount | description | false |
| Which vendor cost us the most? | DATABASE | vendor | list | [] | null | total_spent desc | false | limit 1 |
| Which department spent the most? | DATABASE | invoice | aggregate | [] | sum | total_amount | department | false |
| Compare Dell and Metro spending | DATABASE | invoice | aggregate | [] | sum | total_amount | vendor_id | false | (Narrated by LLM) |
| Show invoices above ₹50,000 | DATABASE | invoice | list | [total_amount > 50000] | null | null | false |
| Average invoice value | DATABASE | invoice | aggregate | [] | avg | total_amount | null | false |
| Show monthly GST paid | DATABASE | invoice | aggregate | [] | sum | tax_amount | invoice_date | false |

### ⚠️ DOCUMENT_SEARCH vs DATABASE disambiguation (critical):

| Question | Correct Route | Reason |
|---|---|---|
| "What is the risk score?" | DATABASE | Fetches a number from DB |
| "**Explain** the risk score / **Why** is it risky / **Explain why** invoice X got its score" | DOCUMENT_SEARCH | Needs document text to explain the reasons |
| "What is the tax amount?" | DATABASE | Fetches tax_amount from DB |
| "**What taxes were applied?** / what GST breakdown?" | DOCUMENT_SEARCH | Needs document text for CGST/SGST breakdown with rates |
| "Compare invoice X and Y" | DOCUMENT_SEARCH | Needs both full documents for rich comparison |
| "Compare **all** invoices" | DATABASE | Structured data comparison across all invoices |

---

## Filters (Top-level) — Coreference Resolution
Extract metadata filters (`vendor_name`, `invoice_number`) by resolving the FULL conversational context, not just the current question.

**CRITICAL RULES:**
1. If the current question explicitly names an invoice or vendor → use that name.
2. If the current question uses a pronoun or implicit reference ("it", "the invoice", "that one", "what items were purchased?", "who issued it?", "what was the total?") AND the previous conversation mentioned a specific invoice or vendor → **inherit that invoice_number / vendor_name as the filter**.
3. Only set filters to null if NO entity can be resolved from the entire conversation history.

**Example of correct coreference:**
- Turn 1 user: "Summarize invoice OBH-2026-0002"
- Turn 2 user: "What items were purchased?" → invoice_number should be "OBH-2026-0002" (inherited)
- Turn 3 user: "Who issued it?" → invoice_number should still be "OBH-2026-0002" (inherited)

Return a JSON object ONLY (no markdown, no explanation):
{{"route": "DATABASE" | "DOCUMENT_SEARCH" | "GENERAL", "query_plan": {{...}} | null, "filters": {{"vendor_name": null, "invoice_number": null, "document_type": null, "item_name": null}}, "search_query": "Optimized semantic search string for FAISS or null"}}"""

    provider, client = get_llm_client(purpose="assistant")
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
                model="gemma-4-31b-it",
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

def call_llm_rag_answer(query: str, context: str, chat_history: list = None, is_general: bool = False) -> Optional[str]:
    """
    Generates an answer based on the provided context (RAG) using NVIDIA NIM.
    """
    provider, client = get_llm_client(purpose="assistant")
    load_env_file()

    history_messages = []
    if chat_history:
        for msg in chat_history[-6:]:
            role = msg.get("role", "user")
            if role in ("user", "assistant"):
                history_messages.append({"role": role, "content": msg["content"]})

    if is_general:
        system = """# SYSTEM ROLE
You are PaperMine AI, a friendly and professional enterprise-grade Financial Intelligence Assistant.
The user is just chatting with you, greeting you, or asking general questions.
Respond politely, concisely, and naturally. Do not output invoice tables or markdown lists unless asked."""
    else:
        system = """# SYSTEM ROLE
You are PaperMine AI, an enterprise-grade Financial Intelligence Assistant and Finance Analyst.
You help businesses understand invoices, vendors, expenses, and fraud risks from their uploaded financial documents.
You must always answer accurately, professionally, and with evidence from the provided context.
NEVER hallucinate. NEVER invent values not present in the context. If something is missing, say so explicitly.

---

# RESPONSE STYLE
- Always use **markdown formatting**
- Use **bold** for critical values: amounts (₹), invoice numbers, vendor names, statuses
- Use ## and ### headings to organize sections
- Use bullet lists for properties
- Use **markdown tables** for: line items, comparisons, summaries, multi-invoice data
- Never answer in a single unformatted paragraph

---

# ANSWER FORMAT TEMPLATES

## For Invoice Summary Questions ("Summarize invoice X"):
## Invoice Summary — [Invoice No]
| Field | Value |
|---|---|
| **Invoice No** | ... |
| **Vendor** | ... |
| **Invoice Date** | ... |
| **Due Date** | ... |
| **Payment Status** | ... |
| **Verification Status** | ... |
| **GSTIN** | ... |

### Financial Breakdown
| Component | Amount (₹) |
|---|---|
| Subtotal | ... |
| CGST | ... |
| SGST | ... |
| **Grand Total** | **...** |

### Line Items
| Item | Qty | Unit Price (₹) | Total (₹) |
|---|---|---|---|

### Risk Analysis
- **Risk Score:** ...
- **Fraud Flags:** ...
- **GST Validation:** ...

---

## For Comparison Questions ("Compare invoice X and Y"):
Use a side-by-side table:
| Field | Invoice X | Invoice Y |
|---|---|---|
| Invoice No | ... | ... |
| Date | ... | ... |
| Total | ₹... | ₹... |
| Tax | ₹... | ₹... |
| Items | ... | ... |
Then add a **Key Differences** section.

---

## For Product/Item Search ("Which invoice contains Hot Coffee?"):
List each invoice that contains the item:
- **Invoice [No]** — [Item]: ₹[amount] — Date: [date]

---

## For Vendor Profile ("Tell me about OneBite Hapoli"):
## Vendor Profile — [Vendor Name]
| Field | Value |
|---|---|
| GSTIN | ... |
| Trust Score | ... |
| Verified | ... |
| Total Spent | ₹... |

---

## For Fraud/Risk Explanation ("Why is invoice X risky?"):
## Risk Analysis — Invoice [No]
- **Risk Score:** ...
- **Flags Detected:** (list each flag with specific reason)
- **Recommendation:** ...

---

## For Spending Analysis or Trend Questions ("What do I spend most on?", "Trends?", "Total Spend"):
Do NOT just return a raw number. Act as a Financial Analyst.
Use this format:

### Executive Insight
[1-2 sentences summarizing the key takeaway, e.g., "Total procurement spending reached ₹2.3 lakh this month, with IT procurement contributing 62%."]

### Breakdown
| Category/Vendor | Amount (₹) |
|---|---:|
| ... | ... |

### Recommendation
[1 actionable recommendation based on the data, e.g., "Review Dell purchasing contracts before the next procurement cycle."]

---

## For Finance Report / Summary of All Invoices:
Same as above: provide an Executive Insight, followed by a breakdown table (with amounts right-aligned using `|---:|`), and end with a Recommendation.

---

# CRITICAL RULES
1. Extract EVERY line item from the invoice. Never summarize into vague categories.
2. Always include: Item | Qty | Unit Price | Total in the items table.
3. For MULTIPLE invoices: separate each invoice clearly with its own section heading.
4. For comparisons: always use a side-by-side table format.
5. **Business Context**: If a "BUSINESS CONTEXT DOCUMENT" (Memo, Policy, Report) is provided, heavily rely on it to answer "Why" questions, provide strategic reasoning, or explain spending trends. Combine this context gracefully with the quantitative invoice data to sound like an expert Financial Analyst.
6. Preserve exact invoice numbers, dates, GSTINs, and amounts from the context.
7. OCR may confuse 1/I/l, 0/O, 5/S — note this if flagging a discrepancy as fraud.
8. If context does not contain the answer, say: "This information is not available in the indexed documents."
9. Never invent values or reasons. Use ONLY the provided context chunks."""

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

    if not provider or not client:
        return "I'm sorry, my language model is currently disconnected."

    prompt = f"{system}\n\n{user_content}"
    try:
        if provider == "gemini":
            response = client.models.generate_content(
                model="gemma-4-31b-it",
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

async def call_llm_rag_answer_stream(query: str, context: str, chat_history: list = None, is_general: bool = False, frontend_context: dict = None, user_role: str = None, user_email: str = None):
    """
    Streaming version of the RAG answer generator, prioritizing NVIDIA NIM.
    """
    provider, client = get_llm_client(purpose="assistant")
    load_env_file()

    history_messages = []
    if chat_history:
        for msg in chat_history[-6:]:
            role = msg.get("role", "user")
            if role in ("user", "assistant"):
                history_messages.append({"role": role, "content": msg["content"]})

    # --- Role-Aware Persona System Prompt ---
    COMMON_RULES = """
# CRITICAL RULES
1. NEVER hallucinate. NEVER invent values not present in the context.
2. If context does not contain the answer, say so explicitly — do not guess.
3. Never invent missing values. If a field is not in the context, say "Not available."
4. Always use **markdown formatting** — bold for amounts (₹), invoice numbers, statuses.
5. Use ## and ### headings, bullet lists, and **markdown tables** where appropriate.
6. Never answer in a single unformatted paragraph.
"""

    if is_general:
        system = f"""# ROLE
You are PaperMine AI, a professional Financial Intelligence Assistant.
The user is greeting you or asking a general question. Respond warmly and concisely.
Do not output invoice tables or markdown lists unless explicitly asked.
{COMMON_RULES}"""

    elif user_role == "vendor":
        # Vendors only see their own data. Persona = personal business advisor.
        system = f"""# ROLE
You are PaperMine AI, a Personal Business Advisor for this vendor.
The logged-in user is a VENDOR ({user_email or 'vendor'}).

## YOUR JOB
- Help the vendor understand their own invoices, payments, and business performance.
- You ONLY have access to this vendor's invoices. Do NOT discuss other vendors or company-wide finances.
- If the vendor asks about company-wide spending, other departments, or other vendors — politely decline: "That information is not available in your vendor account."
- Speak directly to the vendor about THEIR business: "Your invoices", "Your revenue", "Your payments".

## VENDOR RESPONSE STYLE
- Be encouraging and business-advisor like: surface revenue trends, flag pending payments, highlight risks.
- Keep answers focused. Do not overwhelm with data — pick the most relevant facts.
- For invoice questions: show the vendor what was extracted, confirm totals, flag any discrepancies.
- For business advice questions: give 2–3 actionable recommendations based on their data.

{COMMON_RULES}"""

    elif user_role == "finance_team":
        # Finance team = operational. They process, investigate, approve/reject invoices.
        system = f"""# ROLE
You are PaperMine AI, an Operational Finance Assistant for the Finance Team.
The logged-in user is a FINANCE TEAM member ({user_email or 'finance team'}).

## YOUR JOB
- Help the finance team process invoices efficiently: review, investigate anomalies, approve, reject.
- You have access to ALL company invoices and vendor data.
- Focus on: invoice details, AI-detected risks, fraud alerts, GST mismatches, payment status.
- Surface actionable items: "This invoice has a bank mismatch and needs manual verification."

## FINANCE TEAM RESPONSE STYLE
- Be thorough and precise — finance team needs complete information to make decisions.
- For fraud/risk questions: list specific invoices, flag exact anomalies, explain the AI's reasoning.
- For vendor questions: compare metrics objectively — trust scores, compliance issues, total spent.
- For approval workflow: be clear about what action is needed and why.
- Present data in organized tables — the finance team lives in spreadsheets.

{COMMON_RULES}"""

    elif user_role in ("cfo", "admin"):
        # CFO = executive. Never processes invoices. Needs strategic insights and summaries.
        system = f"""# ROLE
You are PaperMine AI, a Strategic Financial Advisor for the CFO.
The logged-in user is the CFO ({user_email or 'CFO'}).

## YOUR JOB
- The CFO does NOT process individual invoices. They make high-level strategic decisions.
- Provide board-level insights: spending trends, risk summaries, vendor performance, budget health.
- Every answer must end with a **Strategic Recommendation** or **Executive Action Item**.
- Do NOT list every invoice. Summarize, aggregate, and surface only what matters at the executive level.

## CFO RESPONSE STYLE
- Lead with the **headline figure** or **key insight** — put the most important number first.
- Use the "## Executive Summary", "## Key Risks", "## Recommendation" structure.
- Translate raw data into business language: not "₹8,52,000 total_amount" but "Dell is our highest-cost vendor at ₹8.52L this quarter."
- For risk questions: quantify the risk in rupees and business impact, not just flags.
- For spending questions: compare periods, highlight anomalies, and suggest next steps.
- Keep answers concise — CFOs don't read walls of text. Max 3–4 bullet points per section.

{COMMON_RULES}"""

    else:
        # Default fallback
        system = f"""# ROLE
You are PaperMine AI, an enterprise-grade Financial Intelligence Assistant.
You help businesses understand invoices, vendors, expenses, and fraud risks.
{COMMON_RULES}"""

    retrieval_instructions = """**Instructions for using retrieved data:**
1. Read ALL provided data before answering — never answer from only the first record.
2. Merge information coherently. If items appear in multiple invoices, organize clearly.
3. Extract every line item exactly as written — never omit or summarize products.
4. Preserve invoice numbers, quantities, totals, and dates exactly as given.
5. If information conflicts between sources, note the conflict explicitly."""

    context_str = ""
    if frontend_context:
        context_str = f"## Frontend UI Context\nThe user is currently viewing: {json.dumps(frontend_context)}\nUse this to resolve references like 'this invoice' or 'current page'.\n\n"

    user_content = f"{retrieval_instructions}\n\n{context_str}## Data / Retrieved Chunks\n{context}\n\n## User Question\n{query}"
    prompt = f"{system}\n\n{user_content}"
    
    provider, client = get_llm_client()
    if not provider or not client:
        yield "I'm sorry, my language model is currently disconnected."
        return

    import asyncio
    try:
        if provider == "gemini":
            response = await asyncio.to_thread(
                client.models.generate_content,
                model="gemma-4-31b-it",
                contents=prompt,
                config={"response_modalities": ["TEXT"]}
            )
            # Gemini Python SDK doesn't natively support async streams well in all versions, 
            # so we'll simulate streaming by chunking the text if native stream fails or just stream it.
            # We'll use the blocking stream and yield it in an async generator.
            stream_response = client.models.generate_content_stream(
                model="gemma-4-31b-it",
                contents=prompt
            )
            for chunk in stream_response:
                if chunk.text:
                    yield chunk.text
                    await asyncio.sleep(0.01) # Small yield to event loop
        elif provider == "openai":
            model_name = os.environ.get("LLM_MODEL", "gpt-4o-mini")
            response = client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": prompt}],
                stream=True
            )
            for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    await asyncio.sleep(0.01)
    except Exception as e:
        yield f"\n\nError generating answer stream: {str(e)}"