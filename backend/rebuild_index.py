"""One-shot script: re-embed all DB chunks into a fresh FAISS index."""
import os
from dotenv import load_dotenv
load_dotenv()

from app.db.database import SessionLocal
from app.services.vector_store import knowledge_engine

db = SessionLocal()
knowledge_engine.rebuild_index_from_db(db)
db.close()
print("Done. Index now has", knowledge_engine.index.ntotal, "vectors.")
