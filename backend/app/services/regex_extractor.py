import re
import unicodedata
from typing import Optional, List, Dict, Any

# ── Label Synonyms (India-focused: GST invoices, packing lists, bills) ───────

LABELS: Dict[str, List[str]] = {
    "invoice_number": [
        "invoice no", "invoice number", "invoice #", "bill no", "bill number",
        "inv no", "inv.no", "number", "no.", "b111 no", "b1ll no", "bi11 no",
    ],
    "invoice_date": ["invoice date", "date", "dated", "bill date"],
    "gstin": ["gstin", "gst no", "gst number", "gstin/uin"],
    "place_of_supply": ["place of supply"],
    "hsn_sac": ["hsn", "sac", "hsn/sac", "hsn code"],
    "total_amount": [
        "total", "grand total", "total amount", "amount payable", "invoice value",
        "total invoice value", "net payable", "tota1", "tota", "totl",
    ],
    "taxable_value": ["taxable value", "taxable amount", "subtotal", "base amount"],
    "cgst_amount": ["cgst"],
    "sgst_amount": ["sgst"],
    "igst_amount": ["igst"],
}

MONEY_RE = re.compile(r"(?:₹|rs\.?|inr)?\s*(\d{1,3}(?:,\d{2,3})+(?:\.\d{1,2})?|\d+(?:\.\d{1,2})?)", re.IGNORECASE)
# requires a comma-grouped run for the first branch (\,\d{2,3})+ -- else falls through
# to the plain \d+ branch, so "50000.00" isn't truncated to "500" by an early partial match.

DATE_RE = re.compile(r"\b(\d{1,2})[/\.\-](\d{1,2})[/\.\-](\d{4}|\d{2})\b")

# GSTIN: 2-digit state code + 10-char PAN + 1-digit entity code + 'Z' + 1 checksum char
GSTIN_RE = re.compile(r"\b(\d{2}[A-Z]{5}\d{4}[A-Z]\d[Z][A-Z\d])\b")

# GSTIN checksum uses a code-31 (base-36-like) alphabet for the check digit
_GSTIN_ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
_GSTIN_FACTORS = [1, 2] * 8  # alternating 1,2 weights over the first 14 chars


def _gstin_checksum_valid(gstin: str) -> bool:
    """Validates the GSTIN check digit (15th character). Returns False for
    anything that isn't even the right shape, so callers can safely use
    this as a hard filter."""
    if not gstin or len(gstin) != 15:
        return False
    code_chars = gstin[:14]
    try:
        total = 0
        for i, ch in enumerate(code_chars):
            idx = _GSTIN_ALPHABET.index(ch)
            product = idx * _GSTIN_FACTORS[i]
            total += product // 36 + product % 36
        check_digit = _GSTIN_ALPHABET[(36 - (total % 36)) % 36]
        return check_digit == gstin[14]
    except ValueError:
        return False  # character not in alphabet -- OCR garbage


def _strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def _normalize(s: str) -> str:
    return _strip_accents(s).lower()


def _parse_money(raw: str) -> Optional[float]:
    if not raw:
        return None
    cleaned = raw.strip().replace(",", "").replace("₹", "").replace("Rs.", "").replace("INR", "")
    try:
        return float(cleaned)
    except ValueError:
        return None


def _find_value_near_label(text_norm: str, original_text: str, keywords: List[str],
                            pattern: re.Pattern, window: int = 140):
    for kw in keywords:
        kw_norm = _normalize(kw)
        spaced_pattern = r"\s*".join(re.escape(c) for c in kw_norm.replace(" ", ""))
        kw_re = re.compile(spaced_pattern)

        match_kw = kw_re.search(text_norm)
        if not match_kw:
            continue

        start_idx = max(0, match_kw.start() - 10)  # small look-behind, mostly look-ahead
        end_idx = min(len(original_text), match_kw.end() + window)
        snippet = original_text[start_idx:end_idx]

        matches = list(pattern.finditer(snippet))
        if matches:
            # prefer the first match AFTER the label (values follow labels, not precede)
            label_end_in_snippet = match_kw.end() - start_idx
            after = [m for m in matches if m.start() >= label_end_in_snippet]
            best_match = after[0] if after else matches[0]
            return best_match
    return None


def _find_gstin(raw_text: str) -> Optional[str]:
    """Returns the first GSTIN candidate that passes the checksum. Falls back
    to an uncorroborated regex match (checksum-failing) only if nothing
    validates -- common with OCR noise on the check digit itself."""
    candidates = GSTIN_RE.findall(raw_text.upper())
    for c in candidates:
        if _gstin_checksum_valid(c):
            return c
    return candidates[0] if candidates else None


def extract_invoice_data(raw_text: str) -> Dict[str, Any]:
    text_norm = _normalize(raw_text)
    data: Dict[str, Any] = {
        "invoice_number": None,
        "invoice_date": None,
        "gstin": None,
        "place_of_supply": None,
        "hsn_sac": None,
        "taxable_value": None,
        "cgst_amount": None,
        "sgst_amount": None,
        "igst_amount": None,
        "total_amount": None,
    }

    # Invoice number -- via label lookup, not a hardcoded field-specific pattern
    num_match = _find_value_near_label(
        text_norm, raw_text, LABELS["invoice_number"],
        re.compile(r"[:\-\s]*([A-Za-z0-9/\-]{2,20})"),
    )
    if num_match:
        val = num_match.group(1).strip(" :-")
        # only fix O->0 confusion where the token is otherwise all-digit-like
        # (avoids corrupting legitimate letters in e.g. "PO-2026-01")
        digit_like = sum(c.isdigit() for c in val) >= sum(c.isalpha() for c in val)
        data["invoice_number"] = val.replace("O", "0") if digit_like else val

    # Date -- anchored to the "date" label, not a blind whole-text search
    # (a blind search can match inside an invoice number like "INV/2026-27/045")
    date_match = _find_value_near_label(text_norm, raw_text, LABELS["invoice_date"], DATE_RE, window=40)
    if date_match:
        data["invoice_date"] = f"{date_match.group(1)}/{date_match.group(2)}/{date_match.group(3)}"

    # GSTIN (checksum-validated)
    data["gstin"] = _find_gstin(raw_text)

    # Place of supply
    place_match = _find_value_near_label(
        text_norm, raw_text, LABELS["place_of_supply"],
        re.compile(r"[:\-\s]*([A-Za-z][A-Za-z\s]{1,29})(?=\n|$)"),
    )
    if place_match:
        data["place_of_supply"] = place_match.group(1).strip(" :-")

    # HSN/SAC
    hsn_match = _find_value_near_label(
        text_norm, raw_text, LABELS["hsn_sac"], re.compile(r"[:\-\s]*(\d{2,8})")
    )
    if hsn_match:
        data["hsn_sac"] = hsn_match.group(1)

    # Money fields
    for field in ("taxable_value", "cgst_amount", "sgst_amount", "igst_amount", "total_amount"):
        match = _find_value_near_label(text_norm, raw_text, LABELS[field], MONEY_RE)
        if match:
            data[field] = _parse_money(match.group(1))

    return data