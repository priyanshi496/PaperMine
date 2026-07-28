import os
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from sqlalchemy.orm import Session
from app.db import models

class KnowledgeEngine:
    def __init__(self, index_path="faiss_index.bin"):
        self.index_path = index_path
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        self.dimension = 384
        
        # Load or create FAISS index
        if os.path.exists(self.index_path):
            self.index = faiss.read_index(self.index_path)
            # Ensure it is an ID map
            if not isinstance(self.index, faiss.IndexIDMap):
                base_index = faiss.IndexFlatL2(self.dimension)
                self.index = faiss.IndexIDMap(base_index)
        else:
            base_index = faiss.IndexFlatL2(self.dimension)
            self.index = faiss.IndexIDMap(base_index)
            
    def _save_index(self):
        faiss.write_index(self.index, self.index_path)

    def embed_and_store(self, db: Session, document_id: int, vendor_id: int, doc_type: str, category: str, synthesized_text: str):
        """
        Embeds the text, stores the metadata in SQLite, and adds the vector to FAISS.
        """
        chunk = models.DocumentChunk(
            document_id=document_id,
            vendor_id=vendor_id,
            document_type=doc_type,
            category=category,
            chunk_text=synthesized_text
        )
        db.add(chunk)
        db.commit()
        db.refresh(chunk)
        
        # 2. Embed the text
        embedding = self.embedding_model.encode([synthesized_text])
        embedding = np.array(embedding).astype('float32')
        
        # 3. Add to FAISS with the DB ID
        ids = np.array([chunk.id]).astype('int64')
        self.index.add_with_ids(embedding, ids)
        
        # 4. Save to disk
        self._save_index()
        
    def semantic_search(self, db: Session, query: str, top_k: int = 5, filters: dict = None):
        """
        Searches FAISS, then fetches the metadata from SQLite, applying hybrid filters if necessary.
        """
        if self.index.ntotal == 0:
            return []
            
        query_embedding = self.embedding_model.encode([query])
        query_embedding = np.array(query_embedding).astype('float32')
        
        # If we have filters, we might want to fetch more from FAISS to allow for post-filtering
        search_k = top_k * 10 if filters else top_k
        search_k = min(search_k, self.index.ntotal)
        
        distances, indices = self.index.search(query_embedding, search_k)
        
        results = []
        for i, idx in enumerate(indices[0]):
            if idx == -1:
                continue
                
            # Fetch from DB
            chunk = db.query(models.DocumentChunk).filter(models.DocumentChunk.id == int(idx)).first()
            if not chunk:
                continue
                
            # Hybrid Filtering
            if filters:
                if filters.get("vendor_id") and chunk.vendor_id != filters.get("vendor_id"):
                    continue
                if filters.get("document_type") and chunk.document_type != filters.get("document_type"):
                    continue
                    
            results.append({
                "chunk_id": chunk.id,
                "document_id": chunk.document_id,
                "vendor_id": chunk.vendor_id,
                "text": chunk.chunk_text,
                "distance": float(distances[0][i])
            })
            
            if len(results) >= top_k:
                break
                
        return results

knowledge_engine = KnowledgeEngine()
