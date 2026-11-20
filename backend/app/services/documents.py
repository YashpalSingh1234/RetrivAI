"""Document validation, ingestion, and owner-scoped metadata operations."""

from __future__ import annotations

import hashlib
import logging
import sqlite3
import time
from typing import Any

from backend.app.core.config import settings
from backend.app.core.database import database, utc_now
from backend.app.core.services import get_embedding_service, get_vector_store
from backend.app.core.security import validate_uploaded_file
from backend.app.ingestion.chunker import DocumentChunker
from backend.app.ingestion.cleaner import clean_document
from backend.app.ingestion.loaders import load_document_bytes


logger = logging.getLogger(__name__)


class DocumentProcessingError(RuntimeError):
    pass


def list_documents(user_id: str) -> list[dict[str, Any]]:
    with database() as connection:
        rows = connection.execute(
            """SELECT id, filename, file_type, size_bytes, status, chunk_count,
                      created_at, error_message
               FROM documents WHERE user_id = ? ORDER BY created_at DESC""",
            (user_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def get_document(user_id: str, document_id: str) -> dict[str, Any] | None:
    with database() as connection:
        row = connection.execute(
            """SELECT id, filename, file_type, size_bytes, sha256, status,
                      chunk_count, created_at, error_message
               FROM documents WHERE id = ? AND user_id = ?""",
            (document_id, user_id),
        ).fetchone()
    return dict(row) if row else None


def process_document(
    user_id: str,
    original_filename: str | None,
    content: bytes,
    declared_content_type: str | None = None,
) -> dict[str, Any]:
    started = time.perf_counter()
    filename, file_type = validate_uploaded_file(original_filename, content, declared_content_type)
    digest = hashlib.sha256(content).hexdigest()
    now = utc_now()
    with database() as connection:
        existing = connection.execute(
            "SELECT * FROM documents WHERE user_id = ? AND sha256 = ?",
            (user_id, digest),
        ).fetchone()
        if existing and existing["status"] == "ready":
            return dict(existing)
        if existing:
            document_id = existing["id"]
            connection.execute(
                """UPDATE documents SET filename = ?, status = 'processing',
                   error_message = NULL WHERE id = ? AND user_id = ?""",
                (filename, document_id, user_id),
            )
        else:
            document_id = hashlib.sha256(f"{user_id}:{digest}".encode("utf-8")).hexdigest()
            connection.execute(
                """INSERT INTO documents(
                     id, user_id, filename, file_type, size_bytes, sha256,
                     status, chunk_count, created_at
                   ) VALUES(?, ?, ?, ?, ?, ?, 'processing', 0, ?)""",
                (document_id, user_id, filename, file_type, len(content), digest, now),
            )

    vector_store = None
    try:
        vector_store = get_vector_store()
        document = load_document_bytes(content, filename)
        document["document_id"] = document_id
        document["user_id"] = user_id
        document = clean_document(document)
        chunker = DocumentChunker(settings.chunk_size, settings.chunk_overlap)
        chunks = chunker.chunk_document(document)
        if not chunks:
            raise DocumentProcessingError("No readable text was found in this document.")
        for chunk in chunks:
            chunk["metadata"]["user_id"] = user_id
        embedded_chunks = get_embedding_service().embed_chunks(chunks)
        vector_store.add_chunks(embedded_chunks)
        with database() as connection:
            connection.execute(
                """UPDATE documents SET filename = ?, file_type = ?, size_bytes = ?,
                   status = 'ready', chunk_count = ?, error_message = NULL
                   WHERE id = ? AND user_id = ?""",
                (filename, file_type, len(content), len(chunks), document_id, user_id),
            )
    except Exception as exc:
        try:
            if vector_store is not None:
                vector_store.delete_document(document_id, user_id)
        except Exception:
            logger.exception("Could not remove partial vector records for a failed upload")
        message = str(exc) if isinstance(exc, (ValueError, DocumentProcessingError)) else "Document processing failed. Check the backend dependencies and model configuration."
        logger.exception("Document processing failed for document %s (%s)", document_id, type(exc).__name__)
        logger.info(
            "document status=failed id=%s error_type=%s duration_ms=%s",
            document_id, type(exc).__name__, round((time.perf_counter() - started) * 1000),
        )
        with database() as connection:
            connection.execute(
                """UPDATE documents SET status = 'failed', error_message = ?
                   WHERE id = ? AND user_id = ?""",
                (message[:500], document_id, user_id),
            )
        raise DocumentProcessingError(message) from exc

    result = get_document(user_id, document_id)
    if result is None:
        raise DocumentProcessingError("The processed document could not be found.")
    logger.info(
        "document status=ready id=%s chunks=%s duration_ms=%s",
        document_id, result["chunk_count"], round((time.perf_counter() - started) * 1000),
    )
    return result


def delete_document(user_id: str, document_id: str) -> bool:
    record = get_document(user_id, document_id)
    if record is None:
        return False
    get_vector_store().delete_document(document_id, user_id)
    with database() as connection:
        connection.execute(
            "DELETE FROM documents WHERE id = ? AND user_id = ?",
            (document_id, user_id),
        )
    return True
