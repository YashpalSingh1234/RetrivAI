"""Cached process-wide instances of expensive ML and vector services."""

from functools import lru_cache

from backend.app.ingestion.embeddings import EmbeddingService
from backend.app.ingestion.vector_store import VectorStore
from backend.app.retrieval.reranker import Reranker
from backend.app.retrieval.retriever import Retriever


@lru_cache(maxsize=1)
def get_embedding_service() -> EmbeddingService:
    return EmbeddingService()


@lru_cache(maxsize=1)
def get_vector_store() -> VectorStore:
    return VectorStore()


@lru_cache(maxsize=1)
def get_retriever() -> Retriever:
    return Retriever(get_embedding_service(), get_vector_store())


@lru_cache(maxsize=1)
def get_reranker() -> Reranker:
    return Reranker()
