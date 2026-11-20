"""Select, format, and cite the final passages sent to answer generation."""

from __future__ import annotations

from backend.app.core.config import settings


def build_context(chunks: list[dict], max_chars: int = settings.max_context_chars) -> tuple[str, list[dict]]:
    context_parts: list[str] = []
    sources: list[dict] = []
    used_chars = 0
    for index, chunk in enumerate(chunks, start=1):
        metadata = chunk.get("metadata") or {}
        text = str(chunk.get("text", "")).strip()
        if not text:
            continue
        remaining = max_chars - used_chars
        if remaining <= 0:
            break
        text = text[:remaining]
        citation_id = f"S{len(sources) + 1}"
        document_name = str(metadata.get("source") or "Document")
        page_number = metadata.get("page_number")
        header = f"[{citation_id}] {document_name}"
        if page_number is not None:
            header += f" — page {page_number}"
        context_parts.append(f"{header}\n{text}")
        used_chars += len(header) + len(text)
        sources.append({
            "citation_id": citation_id,
            "document_id": str(metadata.get("document_id", "")),
            "document": document_name,
            "page": page_number,
            "chunk_index": metadata.get("chunk_index"),
            "text": text,
            "relevance_score": round(float(chunk.get("relevance_score", 0.0)), 4),
        })
    return "\n\n---\n\n".join(context_parts), sources
