import os
import json
from typing import Optional, Dict, Any

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
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )
            return response.text.strip()
        elif provider == "openai":
            model = os.environ.get("LLM_MODEL", "gpt-4o-mini" if not os.environ.get("OPENROUTER_API_KEY") else "google/gemini-2.5-flash")
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"[LLM Service] Structured extraction failed: {e}")
    return None

def call_llm_assistant_intent(query: str, chat_history: list = None) -> Optional[dict]:
    """
    Classifies a user query into STRUCTURED (SQL) or SEMANTIC (RAG).
    Uses Ollama (Qwen3:8B) as primary — free, local, zero latency.
    Falls back to Gemini/OpenAI if Ollama is unavailable.
    """
    load_env_file()
    
    history_str = ""
    if chat_history:
        history_str = "Previous Conversation:\n" + "\n".join(
            [f"{msg['role']}: {msg['content']}" for msg in chat_history[-4:]]
        ) + "\n\n"

    prompt_text = f"""{history_str}The user asked: "{query}"

## Routing Rules

Route to STRUCTURED (SQL) if the query asks for any aggregation, count, or filter on invoice data.
Aggregation keywords: count, how many, total, sum, average, avg, mean, highest, max, maximum, lowest, min, minimum, latest, newest, oldest, pending, verified, duplicate, high-risk, flagged.

Route to SEMANTIC (RAG) ONLY if the query asks about document content, summaries, specific text, payment terms, items purchased, bank details, or names.
Semantic examples: "summarize invoice X", "what items were bought?", "what bank details are mentioned?", "which invoices mention coffee?"

## SQL Template Registry
If STRUCTURED, choose the SINGLE best matching template:

- count_invoices          -> How many invoices total / uploaded?
- verified_invoice_count  -> How many verified / approved invoices?
- pending_invoice_count   -> How many pending / unverified invoices?
- total_spending          -> Total spending / sum of invoice amounts
- average_invoice_amount  -> Average / mean invoice amount
- highest_invoice_amount  -> Highest / maximum / largest invoice amount
- lowest_invoice_amount   -> Lowest / minimum / smallest invoice amount
- latest_invoice          -> Most recent / newest / latest invoice
- oldest_invoice          -> Oldest / earliest invoice
- duplicate_count         -> How many duplicate invoices / alerts?
- high_risk_invoices      -> How many high-risk / flagged invoices?
- vendor_spending         -> Spending for a specific vendor (needs vendor_name filter)
- invoice_by_number       -> Info about a specific invoice number (needs invoice_number filter)

If none of the templates fit, fallback to SEMANTIC.

## Filters
Also extract any metadata filters if explicitly mentioned.

Return a JSON object ONLY (no markdown, no explanation):
{{"intent": "STRUCTURED" | "SEMANTIC", "sql_template": "template_name" | null, "filters": {{"vendor_name": null, "invoice_number": null, "document_type": null}}}}"""

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
                    return json.loads(match.group())
        except Exception as e:
            print(f"[OllamaIntent] Error: {e}")

    # --- Fallback: Gemini / OpenAI ---
    provider, client = get_llm_client()
    if not provider or not client:
        return {"intent": "SEMANTIC", "sql_template": None, "filters": {}}
    try:
        if provider == "gemini":
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt_text
            )
            raw = response.text.strip().removeprefix("```json").removesuffix("```").strip()
            return json.loads(raw)
        elif provider == "openai":
            model_name = os.environ.get("LLM_MODEL", "gpt-4o-mini")
            response = client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": prompt_text}],
                response_format={"type": "json_object"}
            )
            return json.loads(response.choices[0].message.content.strip())
    except Exception as e:
        print(f"[LLM Service] Assistant intent classification failed: {e}")

    return {"intent": "SEMANTIC", "sql_template": None, "filters": {}}

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

    system = (
        "You are PaperMine's Financial AI Assistant. "
        "Answer the user's question using ONLY the provided context snippets. "
        "Be concise and precise. Use Indian Rupee (₹) for amounts. "
        "If the context does not contain the answer, say exactly: "
        "\"I don't have enough information to answer that from the available documents.\""
    )

    user_content = f"""Context from our document database:
{context}

User question: {query}"""

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
