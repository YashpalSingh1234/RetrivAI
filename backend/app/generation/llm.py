"""OpenAI-compatible chat completion client with a safe extractive fallback."""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request

from backend.app.core.config import settings
from backend.app.generation.prompts import INSUFFICIENT_ANSWER, build_messages


class LLMError(RuntimeError):
    pass


def _completion(messages: list[dict[str, str]]) -> str:
    if not settings.llm_api_key:
        raise LLMError("No LLM API key is configured.")
    payload = {
        "model": settings.llm_model,
        "messages": messages,
        "temperature": 0.1,
        "max_tokens": 700,
    }
    if settings.llm_reasoning_effort:
        payload["reasoning_effort"] = settings.llm_reasoning_effort
    request = urllib.request.Request(
        f"{settings.llm_base_url}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {settings.llm_api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=settings.llm_timeout_seconds) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise LLMError(f"The configured language model returned HTTP {exc.code}.") from exc
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise LLMError("The configured language model could not be reached.") from exc
    except Exception as exc:
        raise LLMError("The configured language model request failed.") from exc

    try:
        choice = body["choices"][0]
        if choice.get("finish_reason") == "length":
            raise LLMError("The language model reached its answer length limit.")
        content = choice["message"]["content"]
        if isinstance(content, list):
            content = "\n".join(
                part.get("text", "") for part in content if isinstance(part, dict)
            )
        if not isinstance(content, str) or not content.strip():
            raise ValueError("Empty response")
        return content.strip()
    except (KeyError, IndexError, TypeError, ValueError, AttributeError) as exc:
        raise LLMError("The language model returned an unexpected response.") from exc


_STOP_WORDS = {
    "what", "when", "where", "which", "who", "whom", "whose", "why", "how",
    "the", "and", "for", "with", "from", "that", "this", "are", "was", "were",
    "have", "has", "had", "does", "did", "can", "could", "would", "should",
    "about", "into", "your", "their", "there", "then", "than", "please",
}


def extractive_answer(question: str, sources: list[dict]) -> str:
    """Select source sentences that overlap the question; never add outside facts."""
    terms = {
        word.lower() for word in re.findall(r"[\w'-]+", question)
        if len(word) > 2 and word.lower() not in _STOP_WORDS
    }
    candidates: list[tuple[int, int, str]] = []
    order = 0
    for source in sources:
        sentences = re.split(r"(?<=[.!?])\s+|\n+", source["text"])
        for sentence in sentences:
            cleaned = sentence.strip()
            if len(cleaned) < 25:
                continue
            sentence_terms = {
                word.lower() for word in re.findall(r"[\w'-]+", cleaned)
            }
            overlap = len(terms & sentence_terms)
            if overlap:
                candidates.append((overlap, order, f"{cleaned[:550]} [{source['citation_id']}]"))
            order += 1
    if not candidates:
        source = sources[0]
        excerpt = source["text"].strip()[:550]
        return f"I couldn't compose a summary without a language model. The closest passage says: {excerpt} [{source['citation_id']}]"
    chosen = sorted(candidates, key=lambda item: (-item[0], item[1]))[:3]
    return "Based on the retrieved passages:\n\n" + "\n\n".join(item[2] for item in chosen)


def generate_answer(
    question: str,
    sources: list[dict],
    history: list[dict] | None = None,
) -> tuple[str, str, str | None]:
    if not sources:
        return INSUFFICIENT_ANSWER, "insufficient_context", None
    try:
        messages = build_messages(question, sources, history)
        answer = _completion(messages)
        if answer == INSUFFICIENT_ANSWER:
            return answer, "insufficient_context", None
        cited = set(re.findall(r"\[(S\d+)\]", answer))
        available = {source["citation_id"] for source in sources}
        if not cited or not cited <= available:
            raise LLMError("The language model did not cite valid source passages.")
        return answer, "llm", None
    except LLMError as exc:
        warning = (
            "LLM_API_KEY is not configured; showing an extractive answer."
            if not settings.llm_api_key
            else f"LLM unavailable; showing an extractive answer. {exc}"
        )
        return extractive_answer(question, sources), "extractive", warning
