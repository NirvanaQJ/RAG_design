import os
import time
from typing import List, Dict, Optional

import chromadb
from chromadb.config import Settings as ChromaSettings
from openai import OpenAI

from config import settings


class VectorStoreService:
    def __init__(self):
        os.makedirs(settings.CHROMA_PERSIST_DIR, exist_ok=True)
        self.client = chromadb.PersistentClient(
            path=settings.CHROMA_PERSIST_DIR,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self.collection = self.client.get_or_create_collection(
            name=settings.CHROMA_COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
        self.embedding_client = OpenAI(
            api_key=settings.EMBEDDING_API_KEY or settings.LLM_API_KEY,
            base_url=settings.EMBEDDING_BASE_URL or settings.LLM_BASE_URL,
        )

    def _call_embedding_api(self, texts: List[str]) -> List[List[float]]:
        response = self.embedding_client.embeddings.create(
            model=settings.EMBEDDING_MODEL,
            input=texts,
        )
        embeddings = [item.embedding for item in response.data]
        return embeddings

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        batch_size = 25
        all_embeddings = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            batch_embeddings = self._call_embedding_api(batch)
            all_embeddings.extend(batch_embeddings)
            if i + batch_size < len(texts):
                time.sleep(0.2)

        return all_embeddings

    def embed_query(self, query: str) -> List[float]:
        embeddings = self._call_embedding_api([query])
        return embeddings[0]

    def add_chunks(self, doc_id: int, chunks: List[str]) -> int:
        if not chunks:
            return 0

        embeddings = self.embed_texts(chunks)
        ids = [f"doc_{doc_id}_chunk_{i}" for i in range(len(chunks))]
        metadatas = [{"doc_id": doc_id, "chunk_index": i} for i in range(len(chunks))]

        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=chunks,
            metadatas=metadatas,
        )
        return len(chunks)

    def search(self, query: str, top_k: Optional[int] = None) -> List[Dict]:
        if top_k is None:
            top_k = settings.RETRIEVAL_TOP_K

        query_embedding = self.embed_query(query)
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )

        search_results = []
        if results and results["ids"] and results["ids"][0]:
            for i in range(len(results["ids"][0])):
                search_results.append({
                    "chunk_id": results["ids"][0][i],
                    "content": results["documents"][0][i],
                    "doc_id": results["metadatas"][0][i].get("doc_id"),
                    "chunk_index": results["metadatas"][0][i].get("chunk_index"),
                    "score": 1 - results["distances"][0][i],
                })

        return search_results

    def delete_document_chunks(self, doc_id: int):
        existing = self.collection.get(where={"doc_id": doc_id})
        if existing and existing["ids"]:
            self.collection.delete(ids=existing["ids"])

    def get_collection_stats(self) -> Dict:
        count = self.collection.count()
        return {"total_chunks": count}


vector_store = VectorStoreService()
