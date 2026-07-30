"""
financial_utils.py

Single source of truth for:
- Cleaning currency/amount strings into floats (never silently returns 0)
- Normalizing GSTIN and invoice numbers (so extraction, storage, and
  matching all agree on the same canonical form)
- Fuzzy invoice-number resolution to survive OCR noise

Every place in the codebase that parses an amount or compares a GSTIN /
invoice number should import from here instead of re-implementing its own
version. Divergent copies of this logic (one stripping "Rs", another not,
one uppercasing, another not) is what causes "wrong totals" / "wrong
invoice matches" bugs that only show up in production.
"""

import re
import difflib
from typing import Optional, List


# ---------------------------------------------------------------------------
# Amounts
# ---------------------------------------------------------------------------

def clean_amount(raw) -> Optional[float]:
    """
    Normalize a currency string/number into a float.

    Returns None (not 0.0) when the value can't be parsed, so callers can
    distinguish "genuinely zero" from "couldn't parse this" and report the
    difference instead of silently deflating totals.
    """
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        return float(raw)

    s = str(raw).strip()
    if not s:
        return None

    # Strip common currency markers / separators. Order matters for "Rs."
    for tok in ("₹", "Rs.", "Rs", "INR", ",", " "):
        s = s.replace(tok, "")
    s = s.strip()

    # Handle accounting-style negatives: (1,234.00) -> -1234.00
    negative = False
    if s.startswith("(") and s.endswith(")"):
        s = s[1:-1]
        negative = True

    if not s:
        return None

    try:
        val = float(s)
        return -val if negative else val
    except ValueError:
        return None


def sum_amounts(raw_values: List) -> dict:
    """
    Sums a list of raw amount values, returning both the total and how many
    were skipped due to parse failure, so callers can surface that instead
    of hiding it.
    """
    total = 0.0
    skipped = 0
    for raw in raw_values:
        val = clean_amount(raw)
        if val is None:
            skipped += 1
        else:
            total += val
    return {"total": total, "skipped": skipped, "count": len(raw_values) - skipped}


# ---------------------------------------------------------------------------
# GSTIN
# ---------------------------------------------------------------------------

def normalize_gstin(raw: Optional[str]) -> Optional[str]:
    """
    Canonical GSTIN form: uppercase, no internal/leading/trailing whitespace.
    Apply this the moment a GSTIN is extracted, and again at any comparison
    site — never compare raw extracted strings directly.
    """
    if not raw:
        return None
    cleaned = re.sub(r"\s+", "", raw).strip().upper()
    return cleaned or None


# ---------------------------------------------------------------------------
# Invoice numbers
# ---------------------------------------------------------------------------

def normalize_invoice_number(raw: Optional[str]) -> Optional[str]:
    """
    Canonical invoice-number form used for BOTH storage and comparison.
    Applying this once at extraction time (rather than only at query time)
    means the same physical invoice always yields the same stored value,
    regardless of which extraction run produced it.
    """
    if not raw:
        return None
    s = raw.strip().upper()
    s = re.sub(r"\s+", "", s)
    return s or None


_OCR_SWAPS = [
    ("O", "0"), ("0", "O"),
    ("I", "1"), ("1", "I"), ("L", "1"),
    ("S", "5"), ("5", "S"),
    ("B", "8"), ("8", "B"),
    ("Z", "2"), ("2", "Z"),
]


def invoice_number_variations(number: str) -> List[str]:
    """
    Generate common single-character OCR-confusion variants of an already
    normalized invoice number. Used as fast exact-match candidates before
    falling back to fuzzy matching.
    """
    if not number:
        return []
    variants = {number}
    for a, b in _OCR_SWAPS:
        if a in number:
            variants.add(number.replace(a, b))
    return list(variants)


def fuzzy_find_invoice_number(candidates: List[str], target: str, cutoff: float = 0.82) -> Optional[str]:
    """
    Given stored invoice numbers and a normalized target, find the closest
    match. Uses stdlib difflib to avoid adding a new dependency; swap in
    rapidfuzz.process.extractOne for better scoring/perf if it's already
    in your environment.
    """
    if not candidates or not target:
        return None
    if target in candidates:
        return target
    matches = difflib.get_close_matches(target, candidates, n=1, cutoff=cutoff)
    return matches[0] if matches else None


def resolve_invoice_number(all_stored_numbers: List[str], raw_query_number: str) -> Optional[str]:
    """
    Full resolution pipeline for a user-supplied (possibly OCR-noisy)
    invoice number against a list of stored (already-normalized) numbers.
    """
    target = normalize_invoice_number(raw_query_number)
    if not target:
        return None
    if target in all_stored_numbers:
        return target
    for variant in invoice_number_variations(target):
        if variant in all_stored_numbers:
            return variant
    return fuzzy_find_invoice_number(all_stored_numbers, target)