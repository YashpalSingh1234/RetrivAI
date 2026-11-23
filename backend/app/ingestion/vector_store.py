"""Document passages and cosine retrieval backed by PostgreSQL and pgvector."""

from __future__ import annotations

import json

import numpy as np
from psycopg import Connection
from psycopg.rows import DictRow

from backend.app.core.config import settings


def _vector_parameter(values: np.ndarray | list[float]) -> str:
    vector = np.asarray(values, dtype=np.float32)
    if vector.shape != (settings.embedding_dimension,):
        raise ValueError(f"Expected {settings.embedding_dimension} embedding dimensions.")
    if not vector.any():
        raise ValueError("Cosine similarity requires a nonzero embedding.")
    return json.dumps(vector.tolist(), allow_nan=False, separators=(",", ":"))


class VectorStore:
    def add_chunks(
        self, connection: Connection[DictRow], chunks: list[dict], batch_size: int = 100
    ) -> int:
        if batch_size <= 0:
            raise ValueError("batch_size must be positive")
        with connection.cursor() as cursor:
            for start in range(0, len(chunks), batch_size):
                batch = chunks[start:start + batch_size]
                cursor.executemany(
                    """
                    INSERT INTO document_chunks(
                        id, document_id, content, source, page_number, chunk_index, embedding
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s::vector)
                    ON CONFLICT (id) DO UPDATE SET
                        content = EXCLUDED.content,
                        source = EXCLUDED.source,
                        page_number = EXCLUDED.page_number,
                        chunk_index = EXCLUDED.chunk_index,
                        embedding = EXCLUDED.embedding
                    """,
                    [
                        (
                            chunk["chunk_id"], chunk["metadata"]["document_id"], chunk["text"],
                            chunk["metadata"]["source"], chunk["metadata"].get("page_number"),
                            chunk["metadata"].get("chunk_index"), _vector_parameter(chunk["embedding"]),
                        )
                        for chunk in batch
                    ],
                )
        return len(chunks)

    def search(
        self,
        connection: Connection[DictRow],
        query_embedding: np.ndarray,
        *,
        user_id: str,
        top_k: int = 5,
        document_ids: list[str] | None = None,
    ) -> list[dict]:
        if top_k <= 0:
            raise ValueError("top_k must be positive")
        rows = connection.execute(
            """
            SELECT c.id, c.content, c.source, c.document_id, c.page_number, c.chunk_index,
                   c.embedding <=> %s::vector AS distance
            FROM document_chunks c
            JOIN documents d ON d.id = c.document_id
            WHERE d.user_id = %s AND d.status = 'ready'
              AND (%s::text[] IS NULL OR c.document_id = ANY(%s::text[]))
            ORDER BY distance, c.id
            LIMIT %s
            """,
            (_vector_parameter(query_embedding), user_id, document_ids, document_ids, top_k),
        ).fetchall()
        return [
            {
                "chunk_id": row["id"],
                "text": row["content"],
                "metadata": {
                    "user_id": user_id,
                    "document_id": row["document_id"],
                    "source": row["source"],
                    "page_number": row["page_number"],
                    "chunk_index": row["chunk_index"],
                },
                "distance": float(row["distance"]),
            }
            for row in rows
        ]
