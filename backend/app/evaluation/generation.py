"""Lightweight lexical evaluation helpers; these are signals, not LLM judges."""

from __future__ import annotations

import re


_STOP_WORDS = {
    "the", "and", "for", "with", "from", "that", "this", "are", "was", "were",
    "have", "has", "had", "does", "did", "what", "when", "where", "which", "who",
    "why", "how", "you", "your", "into", "about", "then", "than", "can", "could",
    "would", "should", "their", "there", "they", "them", "not", "but", "also",
}


def _terms(text: str) -> set[str]:
    return {
        token.lower() for token in re.findall(r"[\w'-]+", text)
        if len(token) > 2 and token.lower() not in _STOP_WORDS
    }


def _f1(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    overlap = len(left & right)
    precision = overlap / len(left)
    recall = overlap / len(right)
    return 2 * precision * recall / (precision + recall) if precision + recall else 0.0


def evaluate_generation(
    question: str,
    answer: str,
    context: str,
    expected_answer: str | None = None,
    cited_ids: list[str] | None = None,
    available_ids: list[str] | None = None,
) -> dict[str, float | bool]:
    answer_terms = _terms(answer)
    context_terms = _terms(context)
    question_terms = _terms(question)
    cited = set(cited_ids or [])
    available = set(available_ids or [])
    citation_score = len(cited & available) / len(cited) if cited else 0.0
    return {
        # Token overlap cannot determine entailment. Keep this limitation explicit.
        "faithfulness_proxy": len(answer_terms & context_terms) / len(answer_terms) if answer_terms else 0.0,
        "context_relevance": len(question_terms & context_terms) / len(question_terms) if question_terms else 0.0,
        "answer_relevance": _f1(answer_terms, _terms(expected_answer)) if expected_answer else _f1(answer_terms, question_terms),
        "citation_correctness": citation_score,
        "heuristic_metrics": True,
    }
