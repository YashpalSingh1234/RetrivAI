"""Optional second-stage cross-encoder reranking."""

from __future__ import annotations

import math
from threading import RLock

from backend.app.core.config import settings


class Reranker:
    def __init__(self, model_name: str = settings.reranker_model, enabled: bool = settings.reranker_enabled) -> None:
        self.model_name = model_name
        self.enabled = enabled
        self._model = None
        self.last_warning: str | None = None
        self._lock = RLock()

    def _get_model(self):
        with self._lock:
            if self._model is None:
                from sentence_transformers import CrossEncoder

                self._model = CrossEncoder(self.model_name)
            return self._model

    def rerank(self, question: str, candidates: list[dict], top_n: int | None = None) -> list[dict]:
        self.last_warning = None
        if not candidates:
            return []
        limit = top_n or len(candidates)
        if not self.enabled:
            return sorted(candidates, key=lambda item: item["relevance_score"], reverse=True)[:limit]

        try:
            with self._lock:
                predictions = self._get_model().predict(
                    [(question, item["text"]) for item in candidates],
                    show_progress_bar=False,
                )
            ranked = []
            for item, prediction in zip(candidates, predictions):
                raw_score = float(prediction)
                score = 1 / (1 + math.exp(-max(-50, min(50, raw_score))))
                ranked.append({**item, "rerank_score": score})
            return sorted(ranked, key=lambda item: item["rerank_score"], reverse=True)[:limit]
        except Exception as exc:
            # Reranking improves ordering but retrieval remains useful when the
            # model is unavailable or its weights cannot be downloaded.
            self.last_warning = f"Reranker unavailable; vector ranking was used ({type(exc).__name__})."
            return sorted(candidates, key=lambda item: item["relevance_score"], reverse=True)[:limit]
