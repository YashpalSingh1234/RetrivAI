"""Vector retrieval scoped to the authenticated user's documents."""

from __future__ import annotations

from backend.app.core.database import database
from backend.app.ingestion.embeddings import EmbeddingService
from backend.app.ingestion.vector_store import VectorStore


class Retriever:
    def __init__(
        self,
        embedding_service: EmbeddingService | None = None,
        vector_store: VectorStore | None = None,
    ) -> None:
        self.embedding_service = embedding_service or EmbeddingService()
        self.vector_store = vector_store or VectorStore()

    def retrieve(
        self,
        question: str,
        user_id: str,
        top_k: int = 5,
        document_ids: list[str] | None = None,
    ) -> list[dict]:
        query_vector = self.embedding_service.embed_query(question)
        with database() as connection:
            results = self.vector_store.search(
                connection, query_vector, user_id=user_id, top_k=top_k, document_ids=document_ids
            )
        for item in results:
            item["relevance_score"] = max(0.0, min(1.0, 1.0 - item["distance"]))
        return results
