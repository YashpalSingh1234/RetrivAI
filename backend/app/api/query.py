"""Grounded query and conversation endpoints."""

from __future__ import annotations

import json
import logging
import sqlite3
import time
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status

from backend.app.core.config import settings
from backend.app.core.database import database, utc_now
from backend.app.core.dependencies import check_rate_limit, get_current_user
from backend.app.core.services import get_reranker, get_retriever
from backend.app.generation.llm import generate_answer
from backend.app.models.schemas import (
    ChatRequest,
    ConversationDetail,
    ConversationSummary,
    QueryRequest,
    QueryResponse,
)
from backend.app.retrieval.context import build_context
from backend.app.services.documents import list_documents


router = APIRouter(tags=["query", "chat"], dependencies=[Depends(check_rate_limit)])
logger = logging.getLogger(__name__)
INSUFFICIENT_ANSWER = "I couldn't find enough information in your documents to answer that question."


def _query_pipeline(
    payload: QueryRequest,
    user: dict,
    history: list[dict] | None = None,
    conversation_id: str | None = None,
    request_id: str = "unknown",
) -> dict:
    started = time.perf_counter()
    retrieval_ms = 0
    reranking_ms = 0
    generation_ms = 0
    owned_documents = list_documents(user["id"])
    ready_ids = {item["id"] for item in owned_documents if item["status"] == "ready"}
    if payload.document_ids:
        unknown_ids = set(payload.document_ids) - ready_ids
        if unknown_ids:
            raise HTTPException(status_code=404, detail="One or more selected documents were not found.")
        allowed_ids = payload.document_ids
    else:
        allowed_ids = None

    warnings: list[str] = []
    candidates = []
    sources: list[dict] = []
    answer = INSUFFICIENT_ANSWER
    generation_mode = "insufficient_context"

    if ready_ids:
        try:
            candidate_k = min(settings.max_top_k * 3, max(payload.top_k * 3, payload.top_k))
            retrieval_started = time.perf_counter()
            candidates = get_retriever().retrieve(
                payload.question,
                user_id=user["id"],
                top_k=candidate_k,
                document_ids=allowed_ids,
            )
            retrieval_ms = round((time.perf_counter() - retrieval_started) * 1000)
            reranking_started = time.perf_counter()
            reranker = get_reranker()
            ranked = reranker.rerank(payload.question, candidates, top_n=payload.top_k)
            reranking_ms = round((time.perf_counter() - reranking_started) * 1000)
            if reranker.last_warning:
                warnings.append(reranker.last_warning)
            relevant = [
                item for item in ranked
                if item.get("relevance_score", 0.0) >= settings.min_relevance_score
            ]
            context, sources = build_context(relevant)
            if context and sources:
                generation_started = time.perf_counter()
                answer, generation_mode, generation_warning = generate_answer(
                    payload.question, sources, history
                )
                generation_ms = round((time.perf_counter() - generation_started) * 1000)
                if generation_warning:
                    warnings.append(generation_warning)
        except HTTPException:
            raise
        except Exception as exc:
            # Surface infrastructure errors without exposing document text, keys,
            # or provider response bodies in API responses.
            raise HTTPException(
                status_code=503,
                detail=f"Retrieval is temporarily unavailable ({type(exc).__name__}).",
            ) from exc

    result = {
        "answer": answer,
        "sources": sources,
        "conversation_id": conversation_id,
        "generation_mode": generation_mode,
        "warning": " ".join(warnings) if warnings else None,
        "latency_ms": round((time.perf_counter() - started) * 1000),
        "retrieved_count": len(candidates),
    }
    logger.info(
        "rag request_id=%s mode=%s candidates=%s sources=%s retrieval_ms=%s reranking_ms=%s generation_ms=%s total_ms=%s",
        request_id, generation_mode, len(candidates), len(sources), retrieval_ms,
        reranking_ms, generation_ms, result["latency_ms"],
    )
    return result


@router.post("/query", response_model=QueryResponse)
def query(payload: QueryRequest, request: Request, user: dict = Depends(get_current_user)) -> dict:
    return _query_pipeline(payload, user, request_id=getattr(request.state, "request_id", "unknown"))


def _owned_conversation(connection: sqlite3.Connection, conversation_id: str, user_id: str):
    row = connection.execute(
        "SELECT id, title, created_at, updated_at FROM conversations WHERE id = ? AND user_id = ?",
        (conversation_id, user_id),
    ).fetchone()
    return row


def _history(connection: sqlite3.Connection, conversation_id: str, limit: int = 8) -> list[dict]:
    rows = connection.execute(
        """SELECT role, content FROM messages WHERE conversation_id = ?
           ORDER BY created_at DESC LIMIT ?""",
        (conversation_id, limit),
    ).fetchall()
    return [dict(row) for row in reversed(rows)]


@router.post("/chat", response_model=QueryResponse)
def chat(payload: ChatRequest, request: Request, user: dict = Depends(get_current_user)) -> dict:
    conversation_id = payload.conversation_id or str(uuid.uuid4())
    now = utc_now()
    with database() as connection:
        existing = _owned_conversation(connection, conversation_id, user["id"])
        if payload.conversation_id and existing is None:
            raise HTTPException(status_code=404, detail="Conversation not found.")
        if existing is None:
            connection.execute(
                """INSERT INTO conversations(id, user_id, title, created_at, updated_at)
                   VALUES(?, ?, ?, ?, ?)""",
                (conversation_id, user["id"], payload.question[:80], now, now),
            )
            history: list[dict] = []
        else:
            history = _history(connection, conversation_id)

    result = _query_pipeline(
        payload, user, history, conversation_id,
        getattr(request.state, "request_id", "unknown"),
    )
    with database() as connection:
        connection.execute(
            """INSERT INTO messages(id, conversation_id, role, content, sources_json, created_at)
               VALUES(?, ?, 'user', ?, '[]', ?)""",
            (str(uuid.uuid4()), conversation_id, payload.question, now),
        )
        connection.execute(
            """INSERT INTO messages(id, conversation_id, role, content, sources_json, created_at)
               VALUES(?, ?, 'assistant', ?, ?, ?)""",
            (
                str(uuid.uuid4()), conversation_id, result["answer"],
                json.dumps(result["sources"], ensure_ascii=False), utc_now(),
            ),
        )
        connection.execute(
            "UPDATE conversations SET updated_at = ? WHERE id = ? AND user_id = ?",
            (utc_now(), conversation_id, user["id"]),
        )
    return result


@router.get("/chat/conversations", response_model=list[ConversationSummary])
def get_conversations(user: dict = Depends(get_current_user)) -> list[dict]:
    with database() as connection:
        rows = connection.execute(
            """SELECT c.id, c.title, c.created_at, c.updated_at,
                      COUNT(m.id) AS message_count
               FROM conversations c LEFT JOIN messages m ON m.conversation_id = c.id
               WHERE c.user_id = ? GROUP BY c.id
               ORDER BY c.updated_at DESC LIMIT 100""",
            (user["id"],),
        ).fetchall()
    return [dict(row) for row in rows]


@router.get("/chat/conversations/{conversation_id}", response_model=ConversationDetail)
def get_conversation(conversation_id: str, user: dict = Depends(get_current_user)) -> dict:
    with database() as connection:
        row = _owned_conversation(connection, conversation_id, user["id"])
        if row is None:
            raise HTTPException(status_code=404, detail="Conversation not found.")
        messages = connection.execute(
            """SELECT id, role, content, sources_json, created_at FROM messages
               WHERE conversation_id = ? ORDER BY created_at""",
            (conversation_id,),
        ).fetchall()
    return {
        **dict(row),
        "message_count": len(messages),
        "messages": [
            {
                "id": item["id"],
                "role": item["role"],
                "content": item["content"],
                "sources": json.loads(item["sources_json"] or "[]"),
                "created_at": item["created_at"],
            }
            for item in messages
        ],
    }


@router.delete("/chat/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conversation(conversation_id: str, user: dict = Depends(get_current_user)) -> None:
    with database() as connection:
        cursor = connection.execute(
            "DELETE FROM conversations WHERE id = ? AND user_id = ?",
            (conversation_id, user["id"]),
        )
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Conversation not found.")
