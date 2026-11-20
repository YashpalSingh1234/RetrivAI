"use client";

import { useRef, useState, type DragEvent } from "react";
import { api } from "@/lib/api";
import type { DocumentRecord } from "@/lib/types";

export function DocumentUpload({ onUploaded }: { onUploaded: (document: DocumentRecord) => void }) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [dragging, setDragging] = useState(false);

  async function upload(file?: File) {
    if (!file) return;
    setError("");
    setMessage("");
    const extension = file.name.split(".").pop()?.toLowerCase();
    if (!extension || !["pdf", "docx", "txt"].includes(extension)) {
      setError("Choose a PDF, DOCX, or TXT file.");
      return;
    }
    if (file.size > 20 * 1024 * 1024) {
      setError("This file is larger than 20 MB.");
      return;
    }
    setBusy(true);
    try {
      const document = await api.uploadDocument(file);
      onUploaded(document);
      setMessage(`${document.filename} is ready to search.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed.");
    } finally {
      setBusy(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  return (
    <div className="upload-wrap">
      <input
        ref={inputRef}
        className="visually-hidden"
        type="file"
        accept=".pdf,.docx,.txt,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain"
        onChange={(event) => void upload(event.target.files?.[0])}
      />
      <button
        className={`upload-zone ${dragging ? "dragging" : ""}`}
        type="button"
        disabled={busy}
        onClick={() => inputRef.current?.click()}
        onDragOver={(event: DragEvent<HTMLButtonElement>) => { event.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={(event: DragEvent<HTMLButtonElement>) => { event.preventDefault(); setDragging(false); void upload(event.dataTransfer.files?.[0]); }}
      >
        <span className="upload-icon" aria-hidden="true">{busy ? <span className="spinner" /> : "↑"}</span>
        <span className="upload-copy">
          <strong>{busy ? "Reading and indexing your document…" : "Drop a document here or browse"}</strong>
          <span>PDF, DOCX, or TXT · up to 20 MB</span>
        </span>
        <span className="upload-action">{busy ? "Working" : "Choose file"}</span>
      </button>
      {error && <p className="inline-error upload-feedback" role="alert">{error}</p>}
      {message && <p className="inline-success upload-feedback" role="status">{message}</p>}
      <p className="upload-hint">Your files are scoped to your account. When configured, only retrieved excerpts are sent to your LLM provider.</p>
    </div>
  );
}
