import os
from dotenv import load_dotenv
load_dotenv()

from app.db.database import SessionLocal
from app.services.vector_store import knowledge_engine

db = SessionLocal()
queries = [
    "coffee invoice spending",
    "compare invoice OBH-2026-0001 OBH-2026-0002",
    "risk score OBH-2026-0002 fraud",
    "what is the total amount",
]
for q in queries:
    docs = knowledge_engine.semantic_search(db, q, top_k=2)
    print(f"\n=== {q!r} ===")
    if not docs:
        print("  ❌ No results!")
    for d in docs:
        print(f"  ✅ doc_id={d['document_id']} dist={d['distance']:.1f} → {d['text'][:100]!r}")
db.close()
