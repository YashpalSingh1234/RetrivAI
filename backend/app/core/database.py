"""PostgreSQL persistence for application records and pgvector passages."""

from __future__ import annotations

import secrets
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Iterator

import psycopg
from psycopg import Connection, sql
from psycopg.rows import DictRow, dict_row

from backend.app.core.config import settings


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def database() -> Iterator[Connection[DictRow]]:
    with psycopg.connect(settings.database_url, row_factory=dict_row, connect_timeout=5) as connection:
        yield connection


def initialize_database() -> None:
    dimension = settings.embedding_dimension
    if not 1 <= dimension <= 16_000:
        raise ValueError("EMBEDDING_DIMENSION must be between 1 and 16000.")
    with database() as connection:
        # Serialize schema creation when multiple API workers start together.
        connection.execute("SELECT pg_advisory_xact_lock(1744089514)")
        connection.execute("CREATE EXTENSION IF NOT EXISTS vector")
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS app_meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                filename TEXT NOT NULL,
                file_type TEXT NOT NULL,
                size_bytes BIGINT NOT NULL,
                sha256 TEXT NOT NULL,
                status TEXT NOT NULL,
                chunk_count INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                error_message TEXT,
                UNIQUE(user_id, sha256)
            );
            CREATE INDEX IF NOT EXISTS documents_owner_created
                ON documents(user_id, created_at DESC);
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                title TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS conversations_owner_updated
                ON conversations(user_id, updated_at DESC);
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
                role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
                content TEXT NOT NULL,
                sources_json TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS messages_conversation_created
                ON messages(conversation_id, created_at);
            """
        )
        connection.execute(
            sql.SQL(
                """
                CREATE TABLE IF NOT EXISTS document_chunks (
                    id TEXT PRIMARY KEY,
                    document_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
                    content TEXT NOT NULL,
                    source TEXT NOT NULL,
                    page_number INTEGER,
                    chunk_index INTEGER,
                    embedding vector({}) NOT NULL
                );
                CREATE INDEX IF NOT EXISTS document_chunks_document
                    ON document_chunks(document_id);
                """
            ).format(sql.Literal(dimension))
        )
        stored = connection.execute(
            """SELECT atttypmod FROM pg_attribute
               WHERE attrelid = 'document_chunks'::regclass AND attname = 'embedding'"""
        ).fetchone()
        if stored is None or stored["atttypmod"] != dimension:
            raise ValueError("EMBEDDING_DIMENSION must match the existing document_chunks schema.")
        connection.execute(
            "INSERT INTO app_meta(key, value) VALUES('auth_secret', %s) ON CONFLICT (key) DO NOTHING",
            (secrets.token_urlsafe(48),),
        )


def get_auth_secret() -> bytes:
    with database() as connection:
        row = connection.execute(
            "SELECT value FROM app_meta WHERE key = 'auth_secret'"
        ).fetchone()
        if row is None:
            raise RuntimeError("The database has not been initialized.")
        return str(row["value"]).encode("utf-8")
