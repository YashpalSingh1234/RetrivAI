"use client";

import { useState } from "react";

const steps = [
  { id: "01", label: "Upload", title: "Document arrives", text: "PDF, DOCX, and TXT uploads are checked for size, extension, and readable content.", group: "indexing", icon: "↥" },
  { id: "02", label: "Prepare", title: "Extract & clean", text: "Text is extracted page by page where possible, then normalized while keeping source metadata.", group: "indexing", icon: "⌕" },
  { id: "03", label: "Split", title: "Create passages", text: "Recursive character splitting makes overlapping passages with document, page, and chunk IDs.", group: "indexing", icon: "▤" },
  { id: "04", label: "Embed", title: "Create vectors", text: "A Sentence Transformer converts passages into normalized vectors in a shared semantic space.", group: "indexing", icon: "◌" },
  { id: "05", label: "Search", title: "Retrieve candidates", text: "The question is embedded in the same vector space. Chroma searches only this account's documents.", group: "query", icon: "⌕" },
  { id: "06", label: "Rerank", title: "Score relevance", text: "A cross-encoder refines the candidate order before the final context is selected.", group: "query", icon: "↕" },
  { id: "07", label: "Context", title: "Build cited context", text: "Selected passages are labeled with citation IDs and original document locations.", group: "query", icon: "⌑" },
  { id: "08", label: "Generate", title: "Answer carefully", text: "An optional OpenAI-compatible model answers from the passages. Without a key, an extractive fallback is used.", group: "query", icon: "✳" },
];

function PipelineNodes({ group, selected, onSelect }: { group: string; selected: string | null; onSelect: (id: string) => void }) {
  return (
    <div className={`pipeline-grid ${group === "query" ? "query-grid" : ""}`}>
      {steps.filter((step) => step.group === group).map((step, index, list) => (
        <div className="pipeline-unit" key={step.id}>
          <button className={`pipeline-node ${group} ${selected === step.id ? "selected" : ""}`} type="button" onClick={() => onSelect(step.id)}>
            <span className="node-number">{step.id}</span><span className="node-icon">{step.icon}</span><strong>{step.label}</strong>
          </button>
          {index < list.length - 1 && <span className="pipeline-arrow" aria-hidden="true">→</span>}
        </div>
      ))}
    </div>
  );
}

export function ArchitectureDiagram() {
  const [selected, setSelected] = useState<string | null>(null);
  const activeStep = steps.find((step) => step.id === selected);
  return (
    <div className="architecture-wrap">
      <div className="architecture-legend">
        <span><i className="legend-dot indexing" /> DOCUMENT INDEXING</span>
        <span><i className="legend-dot query" /> QUESTION & ANSWER</span>
      </div>
      <div className="architecture-lanes">
        <div className="architecture-row">
          <div className="lane-label"><span>01</span><strong>INDEXING</strong><small>Once per document</small></div>
          <PipelineNodes group="indexing" selected={selected} onSelect={(id) => setSelected(selected === id ? null : id)} />
          <div className="storage-node"><span className="storage-icon">▦</span><strong>Chroma</strong><small>Private vectors</small></div>
        </div>
        <div className="architecture-row query-row">
          <div className="lane-label"><span>02</span><strong>QUERY</strong><small>Every question</small></div>
          <PipelineNodes group="query" selected={selected} onSelect={(id) => setSelected(selected === id ? null : id)} />
          <div className="answer-node"><span>✳</span><strong>Answer + sources</strong></div>
        </div>
      </div>
      <div className="architecture-details" aria-live="polite">
        {activeStep ? <><span className="detail-number">{activeStep.id}</span><div><strong>{activeStep.title}</strong><p>{activeStep.text}</p></div><button type="button" onClick={() => setSelected(null)} aria-label="Close step details">×</button></> : <><span className="detail-number">↗</span><div><strong>Follow the path</strong><p>Select any step to see what RetrivAI does there. SQLite keeps account, document, and conversation records separate from vector storage.</p></div></>}
      </div>
      <div className="architecture-foot"><span className="privacy-dot" />All retrieval is scoped to the signed-in account<span className="architecture-foot-sep">·</span>Source labels come from stored metadata</div>
    </div>
  );
}
