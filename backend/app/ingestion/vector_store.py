"""Persistent Chroma vector storage with owner-scoped retrieval."""

from __future__ import annotations

from pathlib import Path

import chromadb
import numpy as np

from backend.app.core.config import settings


class VectorStore:
    def __init__(
        self,
        persist_directory: str | Path = settings.vector_db_path,
        collection_name: str = "rag_documents",
    ) -> None:
        path = Path(persist_directory)
        path.mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(path=str(path))
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def add_chunks(self, chunks: list[dict], batch_size: int = 100) -> int:
        if batch_size <= 0:
            raise ValueError("batch_size must be positive")
        if not chunks:
            return 0
        for start in range(0, len(chunks), batch_size):
            batch = chunks[start:start + batch_size]
            self.collection.upsert(
                ids=[chunk["chunk_id"] for chunk in batch],
                documents=[chunk["text"] for chunk in batch],
                embeddings=[chunk["embedding"] for chunk in batch],
                metadatas=[chunk["metadata"] for chunk in batch],
            )
        return len(chunks)

    def search(
        self,
        query_embedding: np.ndarray,
        top_k: int = 5,
        where: dict | None = None,
    ) -> list[dict]:
        if top_k <= 0:
            raise ValueError("top_k must be positive")
        if self.collection.count() == 0:
            return []
        query_vector = np.asarray(query_embedding, dtype=np.float32)
        if query_vector.ndim != 1:
            raise ValueError("Query embedding must be a 1D vector")
        response = self.collection.query(
            query_embeddings=[query_vector.tolist()],
            n_results=min(top_k, self.collection.count()),
            where=where,
            include=["documents", "metadatas", "distances"],
        )
        matches = []
        for chunk_id, text, metadata, distance in zip(
            response["ids"][0],
            response["documents"][0],
            response["metadatas"][0],
            response["distances"][0],
        ):
            matches.append({
                "chunk_id": chunk_id,
                "text": text,
                "metadata": metadata,
                "distance": float(distance),
            })
        return matches

    def delete_document(self, document_id: str, user_id: str | None = None) -> None:
        where = {"document_id": document_id}
        if user_id:
            where = {"$and": [{"document_id": document_id}, {"user_id": user_id}]}
        self.collection.delete(where=where)

    def count(self, where: dict | None = None) -> int:
        return self.collection.count(where=where)
