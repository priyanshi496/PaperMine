"""Check what FAISS actually returns for the failing queries."""
import os
from dotenv import load_dotenv
load_dotenv()

from app.db.database import SessionLocal
from app.services.vector_store import knowledge_engine

db = SessionLocal()

queries = [
    "coffee invoice",
    "compare invoice OBH-2026-0001 OBH-2026-0002",
    "risk score OBH-2026-0002",
]

for q in queries:
    print(f"\n=== Query: {q!r} ===")
    docs = knowledge_engine.semantic_search(db, q, top_k=3)
    if not docs:
        print("  ❌ No results returned!")
    for d in docs:
        print(f"  doc_id={d['document_id']}  distance={d['distance']:.3f}")
        print(f"  text_snippet={d['text'][:150]!r}")
db.close()
