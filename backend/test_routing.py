"""Quick routing accuracy test for the current pipeline."""
import os
from dotenv import load_dotenv
load_dotenv()

from app.services.llm_service import call_llm_assistant_intent

questions = [
    ("what can u do",                                          "GENERAL"),
    ("how many invoices I have uploaded?",                     "DATABASE"),
    ("What are their invoice numbers?",                        "DATABASE"),
    ("Get me invoices which are not verified",                 "DATABASE"),
    ("What purchasing trends do you observe?",                 "DATABASE"),   # ambiguous
    ("Which products are purchased most frequently?",          "DATABASE"),
    ("What recommendations based on my spending?",             "GENERAL"),    # ambiguous
    ("Are there any unusual spending patterns?",               "DATABASE"),
    ("Which invoices deserve manual review?",                  "DATABASE"),
    ("Which invoices mention coffee, how much spent on coffee?","DATABASE"),
    ("Compare invoice OBH-2026-0001 and OBH-2026-0002",       "DOCUMENT_SEARCH"),
    ("Explain why invoice OBH-2026-0002 received its risk score","DOCUMENT_SEARCH"),
]

correct = 0
for q, expected in questions:
    result = call_llm_assistant_intent(q)
    got = result.get("route") if result else "ERROR"
    plan = result.get("query_plan") if result else None
    status = "✅" if got == expected else "❌"
    print(f"{status} [{expected}→{got}] plan={plan is not None} | {q[:70]}")
    if got == expected:
        correct += 1

print(f"\nAccuracy: {correct}/{len(questions)} ({100*correct//len(questions)}%)")
