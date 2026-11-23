"""Document validation, ingestion, and owner-scoped metadata operations."""

from __future__ import annotations

import hashlib
import logging
import time
from typing import Any

from backend.app.core.config import settings
from backend.app.core.database import database, utc_now
from backend.app.core.security import validate_uploaded_file
from backend.app.core.services import get_embedding_service, get_vector_store
from backend.app.ingestion.chunker import DocumentChunker
from backend.app.ingestion.cleaner import clean_document
from backend.app.ingestion.loaders import load_document_bytes


logger = logging.getLogger(__name__)


class DocumentProcessingError(RuntimeError):
    pass


def list_documents(user_id: str) -> list[dict[str, Any]]:
    with database() as connection:
        return connection.execute(
            """SELECT id, filename, file_type, size_bytes, status, chunk_count,
                      created_at, error_message
               FROM documents WHERE user_id = %s ORDER BY created_at DESC""",
            (user_id,),
        ).fetchall()


def get_document(user_id: str, document_id: str) -> dict[str, Any] | None:
    with database() as connection:
        return connection.execute(
            """SELECT id, filename, file_type, size_bytes, sha256, status,
                      chunk_count, created_at, error_message
               FROM documents WHERE id = %s AND user_id = %s""",
            (document_id, user_id),
        ).fetchone()


def process_document(
    user_id: str,
    original_filename: str | None,
    content: bytes,
    declared_content_type: str | None = None,
) -> dict[str, Any]:
    started = time.perf_counter()
    filename, file_type = validate_uploaded_file(original_filename, content, declared_content_type)
    digest = hashlib.sha256(content).hexdigest()
    document_id = hashlib.sha256(f"{user_id}:{digest}".encode("utf-8")).hexdigest()
    failure: Exception | None = None
    message = ""

    with database() as connection:
        connection.execute(
            """INSERT INTO documents(
                 id, user_id, filename, file_type, size_bytes, sha256,
                 status, chunk_count, created_at
               ) VALUES(%s, %s, %s, %s, %s, %s, 'processing', 0, %s)
               ON CONFLICT (user_id, sha256) DO NOTHING""",
            (document_id, user_id, filename, file_type, len(content), digest, utc_now()),
        )
        existing = connection.execute(
            "SELECT * FROM documents WHERE user_id = %s AND sha256 = %s FOR UPDATE",
            (user_id, digest),
        ).fetchone()
        if existing is None:
            raise DocumentProcessingError("The document record was removed. Upload the file again.")
        if existing["status"] == "ready":
            return existing
        document_id = existing["id"]

        try:
            # Retain the document row on failure, but roll back every chunk from the attempt.
            with connection.transaction():
                document = load_document_bytes(content, filename)
                document["document_id"] = document_id
                chunks = DocumentChunker(settings.chunk_size, settings.chunk_overlap).chunk_document(
                    clean_document(document)
                )
                if not chunks:
                    raise DocumentProcessingError("No readable text was found in this document.")
                embedded_chunks = get_embedding_service().embed_chunks(chunks)
                get_vector_store().add_chunks(connection, embedded_chunks)
                result = connection.execute(
                    """UPDATE documents SET filename = %s, file_type = %s, size_bytes = %s,
                       status = 'ready', chunk_count = %s, error_message = NULL
                       WHERE id = %s RETURNING *""",
                    (filename, file_type, len(content), len(chunks), document_id),
                ).fetchone()
        except Exception as exc:
            failure = exc
            message = (
                str(exc) if isinstance(exc, (ValueError, DocumentProcessingError))
                else "Document processing failed. Check the backend dependencies and model configuration."
            )
            logger.exception("Document processing failed for document %s", document_id)
            connection.execute(
                """UPDATE documents SET filename = %s, status = 'failed', error_message = %s
                   WHERE id = %s""",
                (filename, message[:500], document_id),
            )

    elapsed_ms = round((time.perf_counter() - started) * 1000)
    if failure is not None:
        logger.info(
            "document status=failed id=%s error_type=%s duration_ms=%s",
            document_id, type(failure).__name__, elapsed_ms,
        )
        raise DocumentProcessingError(message) from failure

    if result is None:
        raise DocumentProcessingError("The processed document could not be found.")
    logger.info(
        "document status=ready id=%s chunks=%s duration_ms=%s",
        document_id, result["chunk_count"], elapsed_ms,
    )
    return result


def delete_document(user_id: str, document_id: str) -> bool:
    with database() as connection:
        cursor = connection.execute(
            "DELETE FROM documents WHERE id = %s AND user_id = %s",
            (document_id, user_id),
        )
        return cursor.rowcount > 0
