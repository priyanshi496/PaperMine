import os
import json
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

# Standard Pydantic schema for invoice validation
class InvoiceFields(BaseModel):
    supplier_name: Optional[str] = None
    supplier_address: Optional[str] = None
    supplier_gstin: Optional[str] = None
    invoice_number: Optional[str] = None
    invoice_date: Optional[str] = None
    buyer_name: Optional[str] = None
    buyer_address: Optional[str] = None
    buyer_gstin: Optional[str] = None
    place_of_supply: Optional[str] = None
    hsn_sac: Optional[str] = None
    taxable_value: Optional[float] = None
    tax_rate: Optional[Any] = None
    tax_amount: Optional[float] = None
    total_amount: Optional[float] = None
    signature_present: Optional[bool] = None
    reverse_charge: Optional[bool] = None
    shipping_address: Optional[str] = None
    transit_ref: Optional[str] = None
    table: Optional[List[List[Any]]] = None


def merge_extraction(final_text: str) -> Dict[str, Any]:
    """
    Reconciles deterministic regex extraction with Gemini LLM structured extraction.
    - Regex is the source of truth for pattern/checksum fields (GSTIN, invoice date, amounts).
    - LLM is the source of truth for free-text fields (Names, Addresses) and table layout.
    - Each field returns a unified schema with confidence and source metadata.
    """
    # 1. Run regex extraction (deterministic pass)
    from app.services.regex_extractor import extract_invoice_data
    regex_raw = extract_invoice_data(final_text)

    # 2. Run LLM extraction
    from app.services.llm_service import call_llm_structured_extraction
    llm_raw_str = call_llm_structured_extraction(final_text)

    llm_parsed = {}
    if llm_raw_str:
        try:
            # Strip markdown block wrappers if any
            clean_json = llm_raw_str.strip()
            if clean_json.startswith("```"):
                parts = clean_json.split("```")
                if len(parts) > 1:
                    clean_json = parts[1]
                    if clean_json.startswith("json"):
                        clean_json = clean_json[4:]
            clean_json = clean_json.strip("` \n")

            raw_dict = json.loads(clean_json)
            # Validate against Pydantic schema
            validated = InvoiceFields(**raw_dict)
            llm_parsed = validated.model_dump()
        except Exception as e:
            print(f"[Structured Extraction] Pydantic validation failed: {e}")
            try:
                # Direct JSON parse fallback to capture raw data if schema matches partially
                llm_parsed = json.loads(clean_json)
            except Exception:
                pass

    # 3. Map regex fields to standard keys
    regex_mapped = {
        "invoice_number": regex_raw.get("invoice_number"),
        "invoice_date": regex_raw.get("invoice_date"),
        "supplier_gstin": regex_raw.get("gstin"),
        "place_of_supply": regex_raw.get("place_of_supply"),
        "hsn_sac": regex_raw.get("hsn_sac"),
        "taxable_value": regex_raw.get("taxable_value"),
        "total_amount": regex_raw.get("total_amount"),
    }

    # Sum taxes from CGST/SGST/IGST
    cgst = regex_raw.get("cgst_amount")
    sgst = regex_raw.get("sgst_amount")
    igst = regex_raw.get("igst_amount")
    if igst is not None:
        regex_mapped["tax_amount"] = igst
    elif cgst is not None or sgst is not None:
        regex_mapped["tax_amount"] = (cgst or 0.0) + (sgst or 0.0)

    # 4. Perform reconciliation & build metadata audit trail
    merged = {}
    standard_keys = [
        "supplier_name", "supplier_address", "supplier_gstin",
        "invoice_number", "invoice_date", "buyer_name", "buyer_address",
        "buyer_gstin", "place_of_supply", "hsn_sac", "taxable_value",
        "tax_rate", "tax_amount", "total_amount", "signature_present",
        "reverse_charge", "shipping_address", "transit_ref", "table"
    ]

    for key in standard_keys:
        regex_val = regex_mapped.get(key)
        llm_val = llm_parsed.get(key)

        # Regex is source of truth for pattern/checksum fields
        if regex_val is not None:
            merged[key] = {
                "value": regex_val,
                "source": "regex",
                "confidence": 1.0,
            }
        elif llm_val is not None:
            merged[key] = {
                "value": llm_val,
                "source": "llm",
                "confidence": 0.85,
            }
        else:
            merged[key] = {
                "value": None,
                "source": "none",
                "confidence": 0.0,
            }

    # Merge any other custom metadata fields that Gemini extracted
    for key, val in llm_parsed.items():
        if key not in standard_keys and val is not None:
            merged[key] = {
                "value": val,
                "source": "llm",
                "confidence": 0.80,
            }

    # 5. Math reconciliation: calculate total from table rows if LLM total is missing or slightly off
    try:
        table_data = merged.get("table", {}).get("value")
        if table_data and len(table_data) > 1:
            headers = table_data[0]
            amount_idx = -1
            for idx, h in enumerate(headers):
                if str(h).lower() in ("amount", "total", "value", "amt"):
                    amount_idx = idx
                    break
            
            if amount_idx != -1:
                row_sum = 0.0
                for row in table_data[1:]:
                    if len(row) > amount_idx:
                        val_str = str(row[amount_idx]).strip().replace(",", "")
                        try:
                            row_sum += float(val_str)
                        except ValueError:
                            pass
                
                if row_sum > 0:
                    total_obj = merged.get("total_amount", {})
                    current_total = total_obj.get("value")
                    
                    # Fetch tax amount if available to reconcile grand total
                    tax_obj = merged.get("tax_amount", {})
                    tax_val = tax_obj.get("value") or 0.0
                    expected_total = row_sum + tax_val
                    
                    if current_total is None:
                        merged["total_amount"] = {
                            "value": expected_total,
                            "source": "calculated",
                            "confidence": 1.0,
                        }
                    elif abs(float(current_total) - expected_total) > 0.01:
                        # Correct using python's sum + tax_amount
                        merged["total_amount"] = {
                            "value": expected_total,
                            "source": "calculated_correction",
                            "confidence": 1.0,
                        }
    except Exception as e:
        print(f"[Structured Extraction] Math fallback calculation error: {e}")

    return merged
