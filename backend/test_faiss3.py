import os
from dotenv import load_dotenv
load_dotenv()

from app.db.database import SessionLocal
from app.db import models

db = SessionLocal()
chunks = db.query(models.DocumentChunk).all()
print(f"Total chunks in DB: {len(chunks)}")
for c in chunks:
    print(f"  doc_id={c.document_id} | text={c.chunk_text[:80]!r}")

from app.services.vector_store import knowledge_engine
idx = knowledge_engine.index
print(f"\nFAISS index total: {idx.ntotal if idx else 'NO INDEX'}")
print(f"KnowledgeEngine dimension: {knowledge_engine.dimension}")

# Check if index file exists
import os
print(f"faiss_index.bin exists: {os.path.exists('faiss_index.bin')}")
db.close()
