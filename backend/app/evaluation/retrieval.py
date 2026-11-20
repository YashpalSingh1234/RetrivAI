"""Deterministic retrieval metrics for offline RAG evaluation."""

from __future__ import annotations


def precision_at_k(relevant_ids: set[str] | list[str], retrieved_ids: list[str], k: int) -> float:
    if k <= 0:
        raise ValueError("k must be positive")
    relevant = set(relevant_ids)
    if not relevant:
        return 0.0
    top = retrieved_ids[:k]
    return len(set(top) & relevant) / k


def recall_at_k(relevant_ids: set[str] | list[str], retrieved_ids: list[str], k: int) -> float:
    if k <= 0:
        raise ValueError("k must be positive")
    relevant = set(relevant_ids)
    if not relevant:
        return 0.0
    return len(set(retrieved_ids[:k]) & relevant) / len(relevant)


def mean_reciprocal_rank(
    relevant_id_sets: list[set[str] | list[str]], retrieved_id_lists: list[list[str]], k: int | None = None
) -> float:
    if len(relevant_id_sets) != len(retrieved_id_lists):
        raise ValueError("Relevant and retrieved result lists must have matching lengths")
    if not relevant_id_sets:
        return 0.0
    scores = []
    for relevant_ids, retrieved_ids in zip(relevant_id_sets, retrieved_id_lists):
        relevant = set(relevant_ids)
        ranking = retrieved_ids if k is None else retrieved_ids[:k]
        score = next((1.0 / rank for rank, item in enumerate(ranking, 1) if item in relevant), 0.0)
        scores.append(score)
    return sum(scores) / len(scores)


def evaluate_retrieval(
    relevant_ids: set[str] | list[str], retrieved_ids: list[str], k: int = 5
) -> dict[str, float]:
    relevant = set(relevant_ids)
    reciprocal_rank = next(
        (1.0 / rank for rank, item in enumerate(retrieved_ids[:k], 1) if item in relevant),
        0.0,
    )
    return {
        "precision_at_k": precision_at_k(relevant, retrieved_ids, k),
        "recall_at_k": recall_at_k(relevant, retrieved_ids, k),
        "reciprocal_rank": reciprocal_rank,
    }
