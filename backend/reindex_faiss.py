import asyncio
from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.models.document import Document
from app.services.vector_store import knowledge_engine
from app.services.intelligence_pipeline import process_document_intelligence

def reindex_all():
    db = SessionLocal()
    docs = db.query(Document).filter(Document.extracted_data != None).all()
    print(f"Found {len(docs)} documents with extracted data.")
    
    # Wipe FAISS index
    knowledge_engine.reset_index()
    print("Wiped existing FAISS index.")
    
    for doc in docs:
        print(f"Re-indexing Doc #{doc.id}...")
        try:
            # Re-run pipeline to generate new two-stage embeddings
            process_document_intelligence(db, doc.id)
            print(f"Doc #{doc.id} done.")
        except Exception as e:
            print(f"Doc #{doc.id} failed: {e}")

    db.close()
    print(f"New index size: {knowledge_engine.index.ntotal}")

if __name__ == "__main__":
    reindex_all()
