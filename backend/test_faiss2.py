"""Check raw vector store state."""
import os
from dotenv import load_dotenv
load_dotenv()

from app.db.database import SessionLocal
from app.db import models

db = SessionLocal()
chunks = db.query(models.DocumentChunk).all()
print(f"Total chunks in DB: {len(chunks)}")
if chunks:
    print("Sample chunk:")
    c = chunks[0]
    print(f"  doc_id={c.document_id}, text={c.chunk_text[:100]!r}")
    print(f"  embedding length={len(c.embedding) if c.embedding else 0}")

import numpy as np
from app.services.vector_store import knowledge_engine
print(f"\nFAISS index total vectors: {knowledge_engine.index.ntotal if knowledge_engine.index else 'NO INDEX'}")
db.close()
