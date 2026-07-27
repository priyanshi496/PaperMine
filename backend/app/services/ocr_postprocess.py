"""
OCR Post-Processing Module
==========================
Cleans up raw PaddleOCR output before it reaches the LLM:
  1. Gibberish detection   — flags unintelligible character sequences
  2. Character substitution — fixes common OCR misrecognitions (0/O, 1/l/I, rn→m)
  3. Broken word merging   — re-joins words split across adjacent OCR boxes
  4. Confidence tagging     — marks low-confidence or gibberish text with
                              [LOW_CONFIDENCE] so the LLM knows to reconstruct
"""

import re
from typing import List

# ── Common English bigrams (top ~40 by frequency) ────────────────────────────
# Used as a quick heuristic: real English text will contain many of these,
# gibberish almost none.
_COMMON_BIGRAMS = {
    "th", "he", "in", "er", "an", "re", "on", "at", "en", "nd",
    "ti", "es", "or", "te", "of", "ed", "is", "it", "al", "ar",
    "st", "to", "nt", "ng", "se", "ha", "as", "ou", "io", "le",
    "ve", "co", "me", "de", "hi", "ri", "ro", "ic", "ne", "ea",
}

# ── Gibberish Detection ─────────────────────────────────────────────────────

def _has_excessive_repetition(text: str, max_repeat: int = 3) -> bool:
    """Detects runs of 3+ identical consecutive characters (e.g. 'eeee')."""
    for i in range(len(text) - max_repeat + 1):
        if len(set(text[i:i + max_repeat])) == 1 and text[i].isalpha():
            return True
    return False


def _bigram_score(text: str) -> float:
    """Returns the fraction of character-bigrams that are common English bigrams.
    Real English text typically scores > 0.25; gibberish scores < 0.10."""
    cleaned = re.sub(r"[^a-z]", "", text.lower())
    if len(cleaned) < 4:
        return 1.0  # too short to judge; assume OK
    bigrams = [cleaned[i:i + 2] for i in range(len(cleaned) - 1)]
    if not bigrams:
        return 1.0
    hits = sum(1 for b in bigrams if b in _COMMON_BIGRAMS)
    return hits / len(bigrams)


def _vowel_ratio(text: str) -> float:
    """Returns the ratio of vowels to total alphabetic characters.
    English text is typically 0.30-0.45; pure consonant gibberish is < 0.10."""
    alpha = [c for c in text.lower() if c.isalpha()]
    if len(alpha) < 3:
        return 0.35  # too short; assume normal
    vowels = sum(1 for c in alpha if c in "aeiou")
    return vowels / len(alpha)


def is_gibberish(text: str) -> bool:
    """Returns True if the text is likely OCR gibberish, not real words."""
    # Skip short tokens and numbers
    stripped = text.strip()
    if len(stripped) < 4:
        return False
    # Skip if mostly digits/punctuation (e.g. amounts, dates)
    alpha_chars = [c for c in stripped if c.isalpha()]
    if len(alpha_chars) < 3:
        return False

    # Check 1: Excessive character repetition (e.g. 'eeee', 'ooo')
    if _has_excessive_repetition(stripped):
        return True

    # Check 2: Very low vowel ratio (consonant soup)
    vr = _vowel_ratio(stripped)
    if vr < 0.08:
        return True

    # Check 3: Very low English bigram score
    bs = _bigram_score(stripped)
    if bs < 0.08:
        return True

    # Check 4: Combined weak signal — both metrics are below-average
    if vr < 0.18 and bs < 0.18:
        return True

    # Check 5: For hyphenated/compound tokens, check each part independently
    # e.g. 'soobbenxopens-easeoog' → check 'soobbenxopens' and 'easeoog'
    parts = re.split(r'[-_]', stripped)
    if len(parts) > 1:
        gibberish_parts = sum(1 for p in parts if len(p) >= 4 and _bigram_score(p) < 0.20)
        if gibberish_parts >= len(parts) * 0.5:
            return True

    return False


# ── Common OCR Character Substitution Fixes ──────────────────────────────────

def _fix_char_substitutions(text: str) -> str:
    """Applies context-aware character substitution fixes for common OCR errors."""
    result = text

    # Fix 'rn' → 'm' only in word contexts (very common OCR confusion)
    # e.g. 'arnount' → 'amount', 'nurnber' → 'number'
    result = re.sub(r'(?<=[a-zA-Z])rn(?=[a-zA-Z])', 'm', result)

    # Fix '1' → 'l' when surrounded by letters (e.g. 'tota1' → 'total')
    result = re.sub(r'(?<=[a-zA-Z])1(?=[a-zA-Z])', 'l', result)

    # Fix 'l' → '1' when surrounded by digits (e.g. '3l.50' → '31.50')
    result = re.sub(r'(?<=\d)l(?=\d)', '1', result)

    # Fix '0' → 'O' at start of words followed by letters (e.g. '0rder' → 'Order')
    result = re.sub(r'\b0(?=[a-zA-Z]{2,})', 'O', result)

    # Fix 'O' → '0' when surrounded by digits (e.g. '1O0.00' → '100.00')
    result = re.sub(r'(?<=\d)O(?=\d)', '0', result)

    # Fix 'S' → '5' when surrounded by digits
    result = re.sub(r'(?<=\d)S(?=\d)', '5', result)

    # Fix '5' → 'S' at start of common words
    result = re.sub(r'\b5(?=ubto|ubtotal|upplier|hipping|ignature)', 'S', result, flags=re.IGNORECASE)

    # Fix 'B' → '8' when surrounded by digits
    result = re.sub(r'(?<=\d)B(?=\d)', '8', result)
    
    # Fix tax percentage errors like {S.00%} -> (5.00%)
    result = re.sub(r'[\{\[\(][Ss5]\.00[%*t][\}\]\)]', '(5.00%)', result)
    
    # Fix common CGST/SGST capitalization and typos
    result = re.sub(r'(?i)\bcgst\b', 'CGST', result)
    result = re.sub(r'(?i)\bsgst\b', 'SGST', result)
    result = re.sub(r'(?i)\bigst\b', 'IGST', result)

    # Fix common OCR word errors on invoice keywords
    _WORD_FIXES = {
        "tota1": "total",
        "tota|": "total",
        "tot@l": "total",
        "arnount": "amount",
        "arnont": "amount",
        "nurnber": "number",
        "nurber": "number",
        "lnvoice": "Invoice",
        "1nvoice": "Invoice",
        "lnv.": "Inv.",
        "b111": "bill",
        "bi11": "bill",
        "b1ll": "bill",
        "supp1ier": "supplier",
        "supp|ier": "supplier",
        "subtota1": "subtotal",
        "quantlty": "quantity",
        "quant1ty": "quantity",
    }
    for wrong, right in _WORD_FIXES.items():
        result = re.sub(re.escape(wrong), right, result, flags=re.IGNORECASE)

    return result


# ── Broken Word Merging ─────────────────────────────────────────────────────

def merge_broken_words(lines: list, x_gap_threshold: float = 5.0) -> list:
    """Merges adjacent OcrLine objects that were split mid-word.
    Two boxes are considered one word if:
      - They are on the same row (similar y-center)
      - The x-gap between them is very small (< x_gap_threshold pixels)
      - Neither ends/starts with a space or punctuation
    """
    if not lines or len(lines) < 2:
        return lines

    merged = []
    i = 0
    while i < len(lines):
        current = lines[i]
        # Look ahead for merge candidates
        while i + 1 < len(lines):
            next_line = lines[i + 1]
            # Same row check (y-center within tolerance)
            curr_y = (current.box[1] + current.box[3]) / 2
            next_y = (next_line.box[1] + next_line.box[3]) / 2
            if abs(curr_y - next_y) > 15:
                break

            # X-gap check
            x_gap = next_line.box[0] - current.box[2]
            if x_gap > x_gap_threshold:
                break

            # Don't merge if current ends or next starts with space/punctuation
            if (current.text.rstrip()[-1:] in (' ', '.', ',', ':', ';', '-', '|') or
                    next_line.text.lstrip()[:1] in (' ', '.', ',', ':', ';', '-', '|')):
                break

            # Merge: concatenate text, union bounding box, average confidence
            current.text = current.text + next_line.text
            current.box = [
                min(current.box[0], next_line.box[0]),
                min(current.box[1], next_line.box[1]),
                max(current.box[2], next_line.box[2]),
                max(current.box[3], next_line.box[3]),
            ]
            current.score = (current.score + next_line.score) / 2
            i += 1

        merged.append(current)
        i += 1

    return merged


# ── Main Post-Processing Entry Point ─────────────────────────────────────────

LOW_CONFIDENCE_TAG = "[LOW_CONFIDENCE]"

def postprocess_ocr_lines(
    lines: list,
    confidence_threshold: float = 0.70,
) -> list:
    """
    Applies all post-processing steps to a list of OcrLine objects:
      1. Merge broken words
      2. Fix common character substitutions
      3. Detect and tag gibberish / low-confidence text

    Modifies lines in-place and returns the same list.
    """
    # Step 1: Merge broken words
    lines = merge_broken_words(lines)

    # Step 2 & 3: Fix substitutions, filter garbage, tag low confidence
    cleaned_lines = []
    for line in lines:
        # Apply character substitution fixes
        fixed_text = _fix_char_substitutions(line.text)
        if fixed_text != line.text:
            line.corrected = fixed_text

        final = line.final_text
        
        # Filter 1: Drop lines that are >80% punctuation/symbols (like dotted lines ------)
        alnum_count = sum(1 for c in final if c.isalnum())
        if len(final.strip()) > 0 and alnum_count / len(final.strip()) < 0.2:
            continue
            
        # Filter 2: Drop absolute garbage (gibberish with very low confidence)
        if line.score < 0.50 and is_gibberish(final):
            continue

        # Check for low confidence
        if line.score < confidence_threshold or is_gibberish(final):
            # Tag the text so the LLM knows to reconstruct it
            if line.corrected is not None:
                line.corrected = f"{LOW_CONFIDENCE_TAG} {line.corrected}"
            else:
                line.corrected = f"{LOW_CONFIDENCE_TAG} {line.text}"
                
        cleaned_lines.append(line)

    return cleaned_lines
