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
    document_id = "evaluation-" + hashlib.sha256(content).hexdigest()
    document = load_document_bytes(content, args.pdf.name)
    document["document_id"] = document_id
    chunks = DocumentChunker().chunk_document(clean_document(document))
    for chunk in chunks:
        chunk["metadata"]["user_id"] = "evaluation"
    embedded = get_embedding_service().embed_chunks(chunks)
    store = get_vector_store()
    store.add_chunks(embedded)

    cases = [json.loads(line) for line in args.dataset.read_text(encoding="utf-8").splitlines() if line.strip()]
    reports: dict[str, list[dict]] = {"vector": [], "reranked": []}
    reranker = Reranker(enabled=True) if args.with_reranker else None
    reranker_warnings: list[str] = []
    where = {"$and": [{"user_id": "evaluation"}, {"document_id": document_id}]}
    for case in cases:
        relevant_phrase = case["relevant_chunk_contains"].casefold()
        relevant_ids = [
            chunk["chunk_id"] for chunk in chunks
            if chunk["metadata"]["source"] == case["relevant_source"]
            and chunk["metadata"]["page_number"] == case["relevant_page"]
            and relevant_phrase in chunk["text"].casefold()
        ]
        query_vector = get_embedding_service().embed_query(case["question"])
        candidates = store.search(query_vector, top_k=args.top_k * 3, where=where)
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
