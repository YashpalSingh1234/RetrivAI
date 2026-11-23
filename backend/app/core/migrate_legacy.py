"""Copy SQLite records and Chroma passages into an empty PostgreSQL database."""

from __future__ import annotations

import argparse
import sqlite3
from collections import Counter
from contextlib import closing
from pathlib import Path
from shutil import copytree
from tempfile import TemporaryDirectory

from psycopg import Connection, sql
from psycopg.rows import DictRow

from backend.app.core.config import PROJECT_ROOT
from backend.app.core.database import database, initialize_database
from backend.app.ingestion.vector_store import VectorStore


TABLE_COLUMNS = {
    "users": "id email password_hash created_at",
    "documents": "id user_id filename file_type size_bytes sha256 status chunk_count created_at error_message",
    "conversations": "id user_id title created_at updated_at",
    "messages": "id conversation_id role content sources_json created_at",
}
IMPORT_MARKER = "legacy_import_v1"
BATCH_SIZE = 100


def _copy_table(source: sqlite3.Connection, target: Connection[DictRow], table: str) -> int:
    columns = TABLE_COLUMNS[table].split()
    rows = source.execute(f"SELECT {', '.join(columns)} FROM {table}")
    insert = sql.SQL("INSERT INTO {} ({}) VALUES ({})").format(
        sql.Identifier(table),
        sql.SQL(", ").join(map(sql.Identifier, columns)),
        sql.SQL(", ").join(sql.Placeholder() for _ in columns),
    )
    total = 0
    with target.cursor() as cursor:
        while batch := rows.fetchmany(BATCH_SIZE):
            cursor.executemany(insert, batch)
            total += len(batch)
    return total


def _copy_passages(
    target: Connection[DictRow], path: Path, ready: dict[str, tuple[str, int]]
) -> tuple[int, int]:
    if not ready:
        return 0, 0
    if not (path / "chroma.sqlite3").is_file():
        raise FileNotFoundError(f"Chroma storage was not found at {path}.")

    import chromadb
    from chromadb.config import Settings as ChromaSettings

    # Open a scratch copy because the Chroma client can update its persistence files.
    with TemporaryDirectory(prefix="retrivai-chroma-import-") as scratch:
        snapshot = copytree(path, Path(scratch) / "chroma")
        client = chromadb.PersistentClient(
            path=str(snapshot), settings=ChromaSettings(anonymized_telemetry=False)
        )
        try:
            collection = client.get_collection("rag_documents")
            store = VectorStore()
            counts: Counter[str] = Counter()
            skipped = 0
            for offset in range(0, collection.count(), BATCH_SIZE):
                batch = collection.get(
                    limit=BATCH_SIZE, offset=offset,
                    include=["embeddings", "documents", "metadatas"],
                )
                chunks = []
                for chunk_id, embedding, content, metadata in zip(
                    batch["ids"], batch["embeddings"], batch["documents"],
                    batch["metadatas"], strict=True,
                ):
                    document_id = (metadata or {}).get("document_id")
                    document = ready.get(document_id)
                    if document is None:
                        skipped += 1
                        continue
                    if metadata.get("user_id") != document[0]:
                        raise ValueError("A Chroma passage owner differs from its SQLite document owner.")
                    chunks.append({
                        "chunk_id": chunk_id, "embedding": embedding,
                        "text": content, "metadata": metadata,
                    })
                    counts[document_id] += 1
                store.add_chunks(target, chunks)

            mismatches = sum(counts[doc_id] != total for doc_id, (_, total) in ready.items())
            if mismatches:
                raise ValueError(
                    f"{mismatches} ready document(s) have different passage counts in SQLite and Chroma."
                )
            return sum(counts.values()), skipped
        finally:
            client.close()


def import_legacy(sqlite_path: Path, chroma_path: Path) -> dict[str, int] | None:
    if not sqlite_path.is_file():
        raise FileNotFoundError(f"SQLite storage was not found at {sqlite_path}.")
    initialize_database()
    with closing(sqlite3.connect(sqlite_path.resolve().as_uri() + "?mode=ro", uri=True)) as source:
        source.execute("BEGIN")
        with database() as target:
            # Block application writes while checking and filling the empty target.
            target.execute(
                """LOCK TABLE app_meta, users, documents, conversations, messages, document_chunks
                   IN SHARE ROW EXCLUSIVE MODE"""
            )
            if target.execute("SELECT 1 FROM app_meta WHERE key = %s", (IMPORT_MARKER,)).fetchone():
                return None
            if target.execute("SELECT 1 FROM users LIMIT 1").fetchone():
                raise ValueError("Import into an empty RetrivAI database before creating accounts.")
            counts = {table: _copy_table(source, target, table) for table in TABLE_COLUMNS}
            ready = {
                document_id: (owner_id, chunk_count)
                for document_id, owner_id, chunk_count in source.execute(
                    "SELECT id, user_id, chunk_count FROM documents WHERE status = 'ready'"
                )
            }
            counts["passages"], counts["skipped_legacy_passages"] = _copy_passages(
                target, chroma_path, ready
            )
            target.execute(
                """UPDATE documents SET status = 'failed', chunk_count = 0,
                   error_message = 'Upload this file again to complete indexing.'
                   WHERE status = 'processing'"""
            )
            with target.cursor() as cursor:
                cursor.executemany(
                    """INSERT INTO app_meta(key, value) VALUES(%s, %s)
                       ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value""",
                    source.execute("SELECT key, value FROM app_meta").fetchall(),
                )
            target.execute(
                "INSERT INTO app_meta(key, value) VALUES(%s, 'complete')", (IMPORT_MARKER,)
            )
            return counts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sqlite", type=Path, default=PROJECT_ROOT / "data/retrivai.sqlite3")
    parser.add_argument("--chroma", type=Path, default=PROJECT_ROOT / "data/chroma_df")
    args = parser.parse_args()
    counts = import_legacy(args.sqlite, args.chroma)
    if counts is None:
        print("The legacy import has already been applied to this database.")
    else:
        print("Imported legacy data into PostgreSQL.")
        for key, total in counts.items():
            print(f"{key}: {total}")


if __name__ == "__main__":
    main()
