import type { SourceCitation as Citation } from "@/lib/types";

export function SourceCitation({ sources }: { sources: Citation[] }) {
  if (!sources.length) return null;
  return (
    <div className="sources-block">
      <div className="sources-heading">Sources <span className="source-count">{sources.length}</span></div>
      <div className="source-grid">
        {sources.map((source) => (
          <details className="source-card" key={`${source.citation_id}-${source.document_id}-${source.chunk_index}`}>
            <summary>
              <span className="citation-tag">{source.citation_id}</span>
              <span className="source-name">
                <strong>{source.document}</strong>
                <small>{source.page ? `Page ${source.page}` : "Document text"}</small>
              </span>
              <span className="source-chevron" aria-hidden="true">⌄</span>
            </summary>
            <div className="source-excerpt">{source.text}</div>
          </details>
        ))}
      </div>
    </div>
  );
}
