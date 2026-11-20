"""Sentence-transformer embeddings shared by ingestion and query retrieval."""

from __future__ import annotations

import numpy as np
import torch
from sentence_transformers import SentenceTransformer
from threading import RLock

from backend.app.core.config import settings


class EmbeddingService:
    def __init__(
        self,
        model_name: str = settings.embedding_model,
        batch_size: int = 32,
        device: str | None = None,
    ) -> None:
        if batch_size <= 0:
            raise ValueError("batch_size must be positive")
        self.model_name = model_name
        self.batch_size = batch_size
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self._model: SentenceTransformer | None = None
        self._embedding_dimension: int | None = None
        self._lock = RLock()

    def _get_model(self) -> SentenceTransformer:
        with self._lock:
            if self._model is None:
                self._model = SentenceTransformer(self.model_name, device=self.device)
                self._embedding_dimension = self._model.get_sentence_embedding_dimension()
            return self._model

    @property
    def embedding_dimension(self) -> int:
        if self._embedding_dimension is None:
            self._get_model()
        assert self._embedding_dimension is not None
        return self._embedding_dimension

    def embed_texts(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.empty((0, self.embedding_dimension), dtype=np.float32)
        if any(not isinstance(text, str) or not text.strip() for text in texts):
            raise ValueError("All texts must be non-empty strings")
        with self._lock:
            embeddings = self._get_model().encode(
                texts,
                batch_size=self.batch_size,
                convert_to_numpy=True,
                normalize_embeddings=True,
                show_progress_bar=False,
            )
        return np.asarray(embeddings, dtype=np.float32)

    def embed_query(self, query: str) -> np.ndarray:
        if not isinstance(query, str) or not query.strip():
            raise ValueError("Query must be a non-empty string")
        return self.embed_texts([query])[0]

    def embed_chunks(self, chunks: list[dict]) -> list[dict]:
        if not chunks:
            return []
        vectors = self.embed_texts([chunk["text"] for chunk in chunks])
        return [
            {**chunk, "embedding": vector.tolist()}
            for chunk, vector in zip(chunks, vectors)
        ]
