"use client";

import { useState } from "react";

const steps = [
  { id: "01", label: "Upload", title: "Document arrives", text: "PDF, DOCX, and TXT uploads are checked for size, extension, and readable content.", group: "indexing", icon: "↥" },
  { id: "02", label: "Prepare", title: "Extract & clean", text: "Text is extracted page by page where possible, then normalized while keeping source metadata.", group: "indexing", icon: "⌕" },
  { id: "03", label: "Split text", title: "Create passages", text: "RetrivAI splits the text into overlapping passages and keeps track of where each one came from.", group: "indexing", icon: "▤" },
  { id: "04", label: "Index", title: "Make passages searchable", text: "A Sentence Transformer represents the meaning of each passage as a set of numbers called a vector.", group: "indexing", icon: "◌" },
  { id: "05", label: "Search", title: "Find related passages", text: "PostgreSQL uses pgvector to compare your question with passages from your documents.", group: "query", icon: "⌕" },
  { id: "06", label: "Rank", title: "Put the best matches first", text: "A ranking model reads the question alongside each match to decide which passages are most relevant.", group: "query", icon: "↕" },
  { id: "07", label: "Cite", title: "Attach sources", text: "RetrivAI records the original document and page for each passage it uses.", group: "query", icon: "⌑" },
  { id: "08", label: "Answer", title: "Return an answer with sources", text: "When an AI model is configured, it writes an answer using the selected passages. Otherwise, RetrivAI shows excerpts from the sources.", group: "query", icon: "✳" },
];

function PipelineNodes({ group, selected, onSelect }: { group: string; selected: string | null; onSelect: (id: string) => void }) {
  return (
    <div className={`pipeline-grid ${group === "query" ? "query-grid" : ""}`}>
      {steps.filter((step) => step.group === group).map((step, index, list) => (
        <div className="pipeline-unit" key={step.id}>
          <button className={`pipeline-node ${group} ${selected === step.id ? "selected" : ""}`} type="button" aria-pressed={selected === step.id} onClick={() => onSelect(step.id)}>
            <span className="node-number">{step.id}</span><span className="node-icon" aria-hidden="true">{step.icon}</span><strong>{step.label}</strong>
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
      <div className="architecture-lanes">
        <div className="architecture-row">
          <div className="lane-label"><h2>Index documents</h2><p>When you upload a file</p></div>
          <PipelineNodes group="indexing" selected={selected} onSelect={(id) => setSelected(selected === id ? null : id)} />
          <div className="storage-node"><span className="storage-icon" aria-hidden="true">▦</span><strong>Search index</strong><small>Stored in PostgreSQL</small></div>
        </div>
        <div className="architecture-row">
          <div className="lane-label"><h2>Answer questions</h2><p>Each time you ask</p></div>
          <PipelineNodes group="query" selected={selected} onSelect={(id) => setSelected(selected === id ? null : id)} />
          <div className="answer-node"><span aria-hidden="true">✳</span><strong>Answer with sources</strong></div>
        </div>
      </div>
      <div className="architecture-details" aria-live="polite">
        {activeStep ? <><span className="detail-number">{activeStep.id}</span><div><strong>{activeStep.title}</strong><p>{activeStep.text}</p></div><button type="button" onClick={() => setSelected(null)} aria-label="Close step details">×</button></> : <p>Select a step to see what happens.</p>}
      </div>
    </div>
  );
}
