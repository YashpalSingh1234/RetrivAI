"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import type { DocumentRecord } from "@/lib/types";

function formatSize(bytes: number) {
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat(undefined, { month: "short", day: "numeric", year: "numeric" }).format(new Date(value));
}

export function DocumentList({
  documents,
  loading,
  onDeleted,
}: {
  documents: DocumentRecord[];
  loading: boolean;
  onDeleted: (id: string) => void;
}) {
  const [deleting, setDeleting] = useState<string | null>(null);
  const [error, setError] = useState("");

  async function remove(document: DocumentRecord) {
    if (!window.confirm(`Remove “${document.filename}” and its indexed passages?`)) return;
    setDeleting(document.id);
    setError("");
    try {
      await api.deleteDocument(document.id);
      onDeleted(document.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Couldn't remove this document.");
    } finally {
      setDeleting(null);
    }
  }

  if (loading && documents.length === 0) return <div className="empty-state">Loading your library…</div>;
  if (documents.length === 0) {
    return (
      <div className="empty-state document-empty">
        <span className="empty-icon" aria-hidden="true">▤</span>
        <strong>Your library is ready for its first document</strong>
        <span>Once indexed, documents become searchable from the chat.</span>
      </div>
    );
  }

  return (
    <div className="document-list-wrap">
      {error && <p className="inline-error" role="alert">{error}</p>}
      <div className="document-list">
        {documents.map((document) => (
          <article className="document-row" key={document.id}>
            <div className={`file-type-badge ${document.file_type.includes("pdf") ? "pdf" : document.file_type.includes("word") ? "docx" : "txt"}`}>
              {document.file_type.includes("pdf") ? "PDF" : document.file_type.includes("word") ? "DOC" : "TXT"}
            </div>
            <div className="document-main">
              <strong title={document.filename}>{document.filename}</strong>
              <span>{formatSize(document.size_bytes)} <i>·</i> Added {formatDate(document.created_at)}</span>
              {document.status === "failed" && document.error_message && <span className="document-error" title={document.error_message}>{document.error_message}</span>}
            </div>
            <div className={`document-status ${document.status}`}>
              <span className="status-dot" />
              {document.status === "ready" ? `${document.chunk_count} passages` : document.status}
            </div>
            <button
              className="icon-button delete-button"
              type="button"
              aria-label={`Delete ${document.filename}`}
              title="Remove document"
              disabled={deleting === document.id}
              onClick={() => void remove(document)}
            >
              {deleting === document.id ? <span className="spinner dark" /> : "×"}
            </button>
          </article>
        ))}
      </div>
    </div>
  );
}
