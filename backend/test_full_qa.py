"""Full routing accuracy test across all question categories."""
import os
from dotenv import load_dotenv
load_dotenv()
from app.services.llm_service import call_llm_assistant_intent

tests = [
    # Single invoice RAG
    ("Summarize invoice OBH-2026-0001",                     "DOCUMENT_SEARCH", None),
    ("What items were purchased in invoice OBH-2026-0001?", "DATABASE",        True),
    ("What is the invoice date?",                            "DATABASE",        True),
    ("What is the due date?",                                "DATABASE",        True),
    ("What is the payment status?",                          "DATABASE",        True),
    ("What is the subtotal?",                                "DATABASE",        True),
    ("What taxes were applied?",                             "DOCUMENT_SEARCH", None),
    ("What are the bank details?",                           "DOCUMENT_SEARCH", None),
    ("What are the payment terms?",                          "DOCUMENT_SEARCH", None),
    ("Is the invoice signed?",                               "DOCUMENT_SEARCH", None),
    # Product questions
    ("Which invoice contains Hot Coffee?",                   "DATABASE",        True),
    ("Which invoices mention Chicken Peppery Sandwich?",     "DATABASE",        True),
    ("Which invoice contains Veg Cheese Burger?",            "DATABASE",        True),
    # Cross-invoice
    ("Compare invoice OBH-2026-0001 and OBH-2026-0002",     "DOCUMENT_SEARCH", None),
    ("Compare all invoices",                                  "DOCUMENT_SEARCH", None),
    ("Which invoice has the highest total?",                  "DATABASE",        True),
    ("Which invoice has the highest GST?",                    "DATABASE",        True),
    ("Which invoice contains the most expensive item?",       "DATABASE",        True),
    # Spending analysis
    ("What do I spend the most money on?",                    "DATABASE",        True),
    ("Which food item appears most frequently?",              "DATABASE",        True),
    ("How much have I spent on coffee?",                      "DATABASE",        True),
    ("How much have I spent on sandwiches?",                  "DATABASE",        True),
    # Time
    ("Show invoices from May",                                "DATABASE",        True),
    ("Which invoice is the latest?",                          "DATABASE",        True),
    ("Which invoice is the oldest?",                          "DATABASE",        True),
    ("List invoices in chronological order",                  "DATABASE",        True),
    # Vendor
    ("Tell me about OneBite Hapoli",                          "DATABASE",        True),
    ("What is my GSTIN?",                                     "DATABASE",        True),
    ("What is my trust score?",                               "DATABASE",        True),
    ("How many invoices have I submitted?",                   "DATABASE",        True),
    # Fraud
    ("Show all fraud alerts",                                 "DATABASE",        True),
    ("Show duplicate invoices",                               "DATABASE",        True),
    ("Explain the risk score for invoice OBH-2026-0002",      "DOCUMENT_SEARCH", None),
    ("Why is invoice OBH-2026-0002 risky?",                   "DOCUMENT_SEARCH", None),
    # Hybrid
    ("Show verified invoices containing coffee",              "DATABASE",        True),
    ("Which invoices over ₹1500 mention French Fries?",       "DATABASE",        True),
    ("Which verified invoices contain Chicken Wrap?",          "DATABASE",        True),
    # Advanced
    ("Give me a financial summary of all invoices",           "DOCUMENT_SEARCH", None),
    ("What purchasing trends do you observe?",                 "DATABASE",        True),
    ("Which products are purchased most frequently?",          "DATABASE",        True),
    ("What recommendations based on my spending?",             "DATABASE",        True),
    ("Generate a monthly expense report",                      "DOCUMENT_SEARCH", None),
]

correct = 0
total = len(tests)
errors = []
for q, expected_route, expect_plan in tests:
    res = call_llm_assistant_intent(q)
    got_route = res.get("route") if res else "ERROR"
    has_plan = res.get("query_plan") is not None
    route_ok = got_route == expected_route
    plan_ok = (expect_plan is None) or (has_plan == expect_plan)
    ok = route_ok and plan_ok
    if ok:
        correct += 1
    else:
        errors.append(f"  ❌ [{expected_route}→{got_route}] plan_expected={expect_plan} plan_got={has_plan} | {q[:70]}")
    print(f"{'✅' if ok else '❌'} [{expected_route}→{got_route}] plan={has_plan} | {q[:60]}")

print(f"\n{'='*60}")
print(f"Accuracy: {correct}/{total} ({100*correct//total}%)")
if errors:
    print("\nFailed questions:")
    for e in errors:
        print(e)
