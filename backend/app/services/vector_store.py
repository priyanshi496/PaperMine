import os
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

import faiss
import numpy as np
from sqlalchemy.orm import Session
from app.db import models

class KnowledgeEngine:
    def __init__(self, index_path="faiss_index.bin"):
        self.index_path = index_path
        
        # --- NVIDIA NEMOTRON-3-EMBED-1B ---
        from openai import OpenAI
        from dotenv import load_dotenv
        load_dotenv()

        class NvidiaEmbeddingWrapper:
            def __init__(self):
                self.client = OpenAI(
                    base_url="https://integrate.api.nvidia.com/v1",
                    api_key=os.environ.get("NVIDIA_API_KEY")
                )

            def encode(self, texts, input_type="passage"):
                response = self.client.embeddings.create(
                    input=texts,
                    model="nvidia/nemotron-3-embed-1b",
                    encoding_format="float",
                    extra_body={"input_type": input_type}
                )
                return [data.embedding for data in response.data]

        self.embedding_model = NvidiaEmbeddingWrapper()
        self.dimension = 2048  # nemotron-3-embed-1b actual output dimension

        # Load or create FAISS index
        if os.path.exists(self.index_path):
            self.index = faiss.read_index(self.index_path)
            if not isinstance(self.index, faiss.IndexIDMap):
                base_index = faiss.IndexFlatL2(self.dimension)
                self.index = faiss.IndexIDMap(base_index)
        else:
            base_index = faiss.IndexFlatL2(self.dimension)
            self.index = faiss.IndexIDMap(base_index)

    def _save_index(self):
        faiss.write_index(self.index, self.index_path)

    def rebuild_index_from_db(self, db: Session):
        """
        Re-embeds all DocumentChunk rows from the DB and rebuilds the FAISS
        index from scratch. Call this when the index file is missing or stale
        (e.g. after changing the embedding model dimension).
        """
        chunks = db.query(models.DocumentChunk).all()
        if not chunks:
            print("[VectorStore] No chunks in DB, nothing to index.")
            return

        print(f"[VectorStore] Rebuilding FAISS index from {len(chunks)} chunk(s)...")
        base_index = faiss.IndexFlatL2(self.dimension)
        self.index = faiss.IndexIDMap(base_index)

        # Batch in groups of 8 to avoid oversized API requests
        BATCH = 8
        for start in range(0, len(chunks), BATCH):
            batch = chunks[start:start + BATCH]
            texts = [c.chunk_text for c in batch]
            try:
                embeddings = self.embedding_model.encode(texts, input_type="passage")
                vectors = np.array(embeddings).astype("float32")
                ids = np.array([c.id for c in batch]).astype("int64")
                self.index.add_with_ids(vectors, ids)
                print(f"[VectorStore]  Indexed chunks {start+1}–{start+len(batch)}")
            except Exception as e:
                print(f"[VectorStore]  Error embedding batch starting at {start}: {e}")

        self._save_index()
        print(f"[VectorStore] Rebuild complete. Total vectors: {self.index.ntotal}")

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

        embedding = self.embedding_model.encode([synthesized_text], input_type="passage")
        embedding = np.array(embedding).astype("float32")

        ids = np.array([chunk.id]).astype("int64")
        self.index.add_with_ids(embedding, ids)
        self._save_index()

    def semantic_search(self, db: Session, query: str, top_k: int = 5, filters: dict = None):
        """
        Searches FAISS with the query embedding (search_query input_type for
        asymmetric retrieval), then fetches metadata from SQLite with optional
        hybrid filters.
        """
        if self.index.ntotal == 0:
            return []

        # Use 'query' input_type for asymmetric retrieval (documents were indexed as 'passage')
        query_embedding = self.embedding_model.encode([query], input_type="query")
        query_embedding = np.array(query_embedding).astype("float32")

        search_k = min(top_k * 10 if filters else top_k, self.index.ntotal)
        distances, indices = self.index.search(query_embedding, search_k)

        results = []
        for i, idx in enumerate(indices[0]):
            if idx == -1:
                continue

            chunk = db.query(models.DocumentChunk).filter(models.DocumentChunk.id == int(idx)).first()
            if not chunk:
                continue

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

