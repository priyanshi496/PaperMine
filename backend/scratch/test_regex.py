import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from app.services.regex_extractor import extract_invoice_data
from app.services.structured_extraction import merge_extraction

text = """
Total Am0unt : Rs 290.00
CGST:(5.00%):Rs 14.50
SGST : (S.00*t) : Rs 14.50
Grand Total : Rs 319.00
"""

import re
MONEY_RE = re.compile(
    r"(?:₹|rs\.?|inr)?\s*"
    r"(?<![A-Za-z0-9])"
    r"("
    r"\d{1,3}(?:,\d{2,3})+(?:\.\d{1,2})?"
    r"|"
    r"\d+(?:\.\d{1,2})?"
    r")"
    r"(?![0-9\.%])"
    , re.IGNORECASE
)

import app.services.regex_extractor
app.services.regex_extractor.MONEY_RE = MONEY_RE
app.services.regex_extractor.LABELS["total_amount"] = [
    "grand total", "total amount", "amount payable", "invoice value",
    "total invoice value", "net payable", "total", "tota1", "tota", "totl",
]

regex_data = extract_invoice_data(text)
print("REGEX RAW WITH NEW MONEY_RE:", regex_data)

merged = merge_extraction(text)
print("MERGED:", merged["total_amount"])
print("TAX:", merged["tax_amount"])
