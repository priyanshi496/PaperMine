import asyncio
from app.db.database import SessionLocal
from app.services.assistant import run_assistant_query_stream
import json

db = SessionLocal()

vendor_questions = [
    "Show all my invoices.",
    "Which invoices are pending payment?",
    "Which invoices were rejected?",
    "Summarize invoice OBH-2026-9999.",
    "What is my total revenue from TechNova?",
]

finance_questions = [
    "How many invoices are waiting?",
    "Show invoices pending approval.",
    "Show duplicate invoices.",
    "Show invoices above ₹50,000.",
    "Show all invoices from Dell.",
]

async def run_query(query, role, vendor_id, email):
    print(f"\n[{role.upper()}] Q: {query}")
    print("-" * 50)
    
    # We collect the SSE chunks
    full_text = ""
    sources = []
    
    gen = run_assistant_query_stream(
        db=db, 
        query=query, 
        chat_history=[], 
        vendor_id=vendor_id, 
        frontend_context={}, 
        user_role=role, 
        user_email=email
    )
    
    async for chunk_str in gen:
        if not chunk_str.startswith("data: "):
            continue
        try:
            data = json.loads(chunk_str[6:].strip())
            if "chunk" in data:
                full_text += data["chunk"]
            if "sources" in data:
                sources = data["sources"]
        except Exception as e:
            pass
            
    print(f"SOURCES: {[s.get('description', s.get('type')) for s in sources]}")
    print(f"RESPONSE:\n{full_text.strip()}")
    print("=" * 50)

async def main():
    print("=== TESTING VENDOR ROLE ===")
    for q in vendor_questions:
        await run_query(q, "vendor", 1, "onebite@vendor.com")
        
    print("\n=== TESTING FINANCE TEAM ROLE ===")
    for q in finance_questions:
        await run_query(q, "finance_team", None, "finance@technova.com")

if __name__ == "__main__":
    asyncio.run(main())
