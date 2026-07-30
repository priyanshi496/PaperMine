"""Test coreference resolution across turns."""
import os
from dotenv import load_dotenv
load_dotenv()

from app.services.llm_service import call_llm_assistant_intent

history = [
    {"role": "user", "content": "Summarize invoice OBH-2026-0002."},
    {"role": "assistant", "content": "Invoice No: OBH-2026-0002, Vendor: OneBite Hapoli..."}
]

followups = [
    "What items were purchased?",
    "What was the total amount?",
    "Who issued it?",
    "What is the risk score?",
]

for q in followups:
    res = call_llm_assistant_intent(q, history)
    inv = res.get("filters", {}).get("invoice_number") if res else None
    route = res.get("route") if res else "ERROR"
    ok = "✅" if inv == "OBH-2026-0002" else "❌"
    print(f"{ok} [{route}] invoice_number={inv!r} | {q}")
