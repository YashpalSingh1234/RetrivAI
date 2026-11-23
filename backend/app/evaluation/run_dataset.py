"""Run the bundled small retrieval dataset against the sample PDF.

Run from the repository root:
    python -m backend.app.evaluation.run_dataset --top-k 5
"""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
from pathlib import Path
from uuid import uuid4

from backend.app.core.database import database, initialize_database, utc_now

from backend.app.core.services import get_embedding_service, get_vector_store
from backend.app.evaluation.retrieval import evaluate_retrieval
from backend.app.ingestion.chunker import DocumentChunker
from backend.app.ingestion.cleaner import clean_document
from backend.app.ingestion.loaders import load_document_bytes
from backend.app.retrieval.reranker import Reranker


ROOT = Path(__file__).resolve().parents[3]
DATASET = Path(__file__).with_name("dataset.jsonl")
SAMPLE_PDF = ROOT / "testdata" / "Big_Data_Basics_Complete_Study_Notes.pdf"


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate semantic retrieval on the sample PDF.")
    parser.add_argument("--dataset", type=Path, default=DATASET)
    parser.add_argument("--pdf", type=Path, default=SAMPLE_PDF)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--with-reranker", action="store_true", help="Also evaluate cross-encoder reranking")
    args = parser.parse_args()
    if args.top_k <= 0:
        parser.error("--top-k must be positive")

    content = args.pdf.read_bytes()
    owner_id = f"evaluation-{uuid4()}"
    document_id = owner_id
    digest = hashlib.sha256(content).hexdigest()
    document = load_document_bytes(content, args.pdf.name)
    document["document_id"] = document_id
    chunks = DocumentChunker().chunk_document(clean_document(document))
    embedded = get_embedding_service().embed_chunks(chunks)
    store = get_vector_store()

    cases = [json.loads(line) for line in args.dataset.read_text(encoding="utf-8").splitlines() if line.strip()]
    reports: dict[str, list[dict]] = {"vector": [], "reranked": []}
    reranker = Reranker(enabled=True) if args.with_reranker else None
    reranker_warnings: list[str] = []
    initialize_database()
    with database() as connection, connection.transaction(force_rollback=True):
        now = utc_now()
        connection.execute(
            "INSERT INTO users(id, email, password_hash, created_at) VALUES(%s, %s, '', %s)",
            (owner_id, f"{owner_id}@example.invalid", now),
        )
        connection.execute(
            """INSERT INTO documents(
                   id, user_id, filename, file_type, size_bytes, sha256, status, chunk_count, created_at
               ) VALUES(%s, %s, %s, 'application/pdf', %s, %s, 'ready', %s, %s)""",
            (document_id, owner_id, args.pdf.name, len(content), digest, len(chunks), now),
        )
        store.add_chunks(connection, embedded)
        for case in cases:
            relevant_phrase = case["relevant_chunk_contains"].casefold()
            relevant_ids = [
                chunk["chunk_id"] for chunk in chunks
                if chunk["metadata"]["source"] == case["relevant_source"]
                and chunk["metadata"]["page_number"] == case["relevant_page"]
                and relevant_phrase in chunk["text"].casefold()
            ]
            query_vector = get_embedding_service().embed_query(case["question"])
            candidates = store.search(
                connection, query_vector, user_id=owner_id, top_k=args.top_k * 3, document_ids=[document_id]
            )
            vector_ids = [item["chunk_id"] for item in candidates[:args.top_k]]
            reports["vector"].append({
                "question": case["question"],
                **evaluate_retrieval(relevant_ids, vector_ids, args.top_k),
            })
            if reranker:
                ranked = reranker.rerank(case["question"], candidates, top_n=args.top_k)
                if reranker.last_warning and reranker.last_warning not in reranker_warnings:
                    reranker_warnings.append(reranker.last_warning)
                reranked_ids = [item["chunk_id"] for item in ranked]
                reports["reranked"].append({
                    "question": case["question"],
                    **evaluate_retrieval(relevant_ids, reranked_ids, args.top_k),
                })

    summary = {
        name: {
            metric: round(statistics.mean(report[metric] for report in rows), 4)
            if rows else 0.0
            for metric in ("precision_at_k", "recall_at_k", "reciprocal_rank")
        }
        for name, rows in reports.items() if rows
    }
    print(json.dumps({
        "top_k": args.top_k,
        "queries": reports,
        "mean": summary,
        "warnings": reranker_warnings,
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
