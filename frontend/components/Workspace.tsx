"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api";
import type { DocumentRecord, Health, User } from "@/lib/types";
import { ArchitectureDiagram } from "@/components/ArchitectureDiagram";
import { AuthPanel } from "@/components/AuthPanel";
import { ChatWindow } from "@/components/ChatWindow";
import { DocumentList } from "@/components/DocumentList";
import { DocumentUpload } from "@/components/DocumentUpload";

type WorkspaceTab = "overview" | "chat" | "documents" | "architecture";

const navItems: { href: string; key: WorkspaceTab; label: string; icon: string }[] = [
  { href: "/", key: "overview", label: "Overview", icon: "⌂" },
  { href: "/chat", key: "chat", label: "Ask your docs", icon: "↗" },
  { href: "/documents", key: "documents", label: "Documents", icon: "▤" },
  { href: "/architecture", key: "architecture", label: "How it works", icon: "⌘" },
];

function titleFor(tab: WorkspaceTab) {
  return ({ overview: "Overview", chat: "Ask your documents", documents: "Your library", architecture: "How RetrivAI works" })[tab];
}

export function Workspace({ active }: { active: WorkspaceTab }) {
  const [user, setUser] = useState<User | null>(null);
  const [health, setHealth] = useState<Health | null>(null);
  const [documents, setDocuments] = useState<DocumentRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [documentsLoading, setDocumentsLoading] = useState(false);
  const [startupError, setStartupError] = useState("");

  const loadDocuments = useCallback(async () => {
    setDocumentsLoading(true);
    try {
      setDocuments(await api.listDocuments());
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) setUser(null);
    } finally {
      setDocumentsLoading(false);
    }
  }, []);

  useEffect(() => {
    let activeEffect = true;
    async function initialize() {
      setLoading(true);
      setStartupError("");
      try {
        const backendHealth = await api.health();
        if (!activeEffect) return;
        setHealth(backendHealth);
      } catch (err) {
        if (activeEffect) {
          setStartupError(err instanceof Error ? err.message : "The backend is not available.");
          setLoading(false);
        }
        return;
      }
      try {
        const currentUser = await api.me();
        if (!activeEffect) return;
        setUser(currentUser);
        setDocuments(await api.listDocuments());
      } catch (err) {
        if (!activeEffect) return;
        if (!(err instanceof ApiError) || err.status !== 401) {
          setStartupError(err instanceof Error ? err.message : "Could not open your workspace.");
        }
        setUser(null);
      } finally {
        if (activeEffect) setLoading(false);
      }
    }
    void initialize();
    return () => { activeEffect = false; };
  }, []);

  async function signOut() {
    try { await api.logout(); } catch { /* Clear the UI even if the backend is restarting. */ }
    setUser(null);
    setDocuments([]);
  }

  if (loading) {
    return <main className="boot-screen"><span className="brand-glyph">R</span><span className="spinner dark" /><p>Opening your workspace…</p></main>;
  }

  if (startupError && !health) {
    return (
      <main className="boot-screen error-screen">
        <span className="brand-glyph">R</span><h1>RetrivAI can’t connect yet</h1><p>{startupError}</p>
        <p className="muted">Start the FastAPI backend on port 8000, then refresh this page.</p>
        <button className="button button-primary" type="button" onClick={() => window.location.reload()}>Try again</button>
      </main>
    );
  }

  if (!user) return <AuthPanel onAuthenticated={(authenticated) => { setStartupError(""); setUser(authenticated); void loadDocuments(); }} />;

  const readyDocuments = documents.filter((document) => document.status === "ready");
  const passageCount = readyDocuments.reduce((total, document) => total + document.chunk_count, 0);

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <Link className="brand" href="/" aria-label="RetrivAI overview"><span className="brand-glyph">R</span><span>Retriv<span className="brand-light">AI</span></span></Link>
        <div className="workspace-switch"><span className="workspace-avatar">{user.email.slice(0, 1).toUpperCase()}</span><span><strong>Personal workspace</strong><small>Private library</small></span><span className="switch-chevron">⌄</span></div>
        <span className="nav-caption">WORKSPACE</span>
        <nav className="side-nav" aria-label="Main navigation">
          {navItems.map((item) => (
            <Link className={active === item.key ? "active" : ""} href={item.href} key={item.key} aria-current={active === item.key ? "page" : undefined}>
              <span className="nav-icon">{item.icon}</span><span>{item.label}</span>{item.key === "documents" && documents.length > 0 && <span className="nav-count">{documents.length}</span>}
            </Link>
          ))}
        </nav>
        <div className="sidebar-spacer" />
        <div className="sidebar-help"><span className="help-icon">?</span><span><strong>Built on evidence</strong><small>Answers link back to source passages.</small></span></div>
        <div className="sidebar-user">
          <div className="user-avatar">{user.email.slice(0, 1).toUpperCase()}</div>
          <div className="user-details"><strong>{user.email.split("@")[0]}</strong><small>{user.email}</small></div>
          <button type="button" className="icon-button signout-button" onClick={() => void signOut()} aria-label="Sign out" title="Sign out">↗</button>
        </div>
        <div className="sidebar-version">RETRIVAI <span>·</span> LOCAL WORKSPACE</div>
      </aside>

      <div className="main-column">
        <header className="topbar">
          <div className="breadcrumb"><span>Workspace</span><i>/</i><strong>{titleFor(active)}</strong></div>
          <div className="topbar-right">
            <span className="backend-indicator"><i />Backend online</span>
            <span className={`model-indicator ${health?.llm_configured ? "configured" : "extractive"}`}>
              <i />{health?.llm_configured ? "LLM connected" : "Extractive mode"}
            </span>
          </div>
        </header>
        {startupError && <div className="workspace-warning" role="alert">{startupError}</div>}
        <main className={`page-content page-${active}`}>
          {active === "overview" && (
            <>
              <div className="page-heading"><div><span className="eyebrow">YOUR KNOWLEDGE, IN CONTEXT</span><h1>A clearer way to find answers.</h1><p>Bring your documents together and ask the questions that matter.</p></div><Link className="button button-primary" href="/chat">Start asking <span>↗</span></Link></div>
              <section className="overview-hero">
                <div className="hero-grid-mark" aria-hidden="true"><span /><span /><span /><span /><span /><span /><span /><span /><span /></div>
                <div className="hero-copy"><div className="hero-label"><span className="hero-star">✳</span> RETRIEVAL-AUGMENTED GENERATION</div><h2>Answers with a trail<br />you can follow.</h2><p>RetrivAI searches your library, gathers the most relevant passages, and returns a concise answer with source citations.</p><Link href="/architecture" className="hero-link">Explore the architecture <span>↗</span></Link></div>
                <div className="hero-orb" aria-hidden="true"><div className="orb-ring ring-one" /><div className="orb-ring ring-two" /><div className="orb-center">R</div><span className="orb-dot dot-one" /><span className="orb-dot dot-two" /><span className="orb-dot dot-three" /></div>
                <div className="hero-footnote"><span className="privacy-dot" />Your sources stay attached to every answer</div>
              </section>
              <section className="stats-grid" aria-label="Workspace overview">
                <div className="stat-card"><span className="stat-label">DOCUMENTS</span><div className="stat-value">{readyDocuments.length}<span className="stat-icon">▤</span></div><span className="stat-note">Ready to search</span></div>
                <div className="stat-card"><span className="stat-label">PASSAGES INDEXED</span><div className="stat-value">{passageCount.toLocaleString()}<span className="stat-icon mint">⌕</span></div><span className="stat-note">Semantic search coverage</span></div>
                <div className="stat-card"><span className="stat-label">ANSWER MODE</span><div className="stat-value mode-value">{health?.llm_configured ? "Generated" : "Extractive"}<span className="stat-icon violet">✳</span></div><span className="stat-note">{health?.llm_configured ? "Grounded by your chosen model" : "Add an LLM key for generated answers"}</span></div>
              </section>
              <section className="content-section">
                <div className="section-heading"><div><span className="eyebrow">BUILD YOUR LIBRARY</span><h2>Add a document</h2></div><span className="section-aside">Step 01 <i>of</i> 02</span></div>
                <DocumentUpload onUploaded={(document) => { setDocuments((items) => [document, ...items.filter((item) => item.id !== document.id)]); }} />
              </section>
              <section className="content-section library-section">
                <div className="section-heading"><div><span className="eyebrow">YOUR SOURCE MATERIAL</span><h2>Recent documents <span className="heading-count">{documents.length}</span></h2></div><Link href="/documents" className="text-link">View library <span>→</span></Link></div>
                <DocumentList documents={documents.slice(0, 5)} loading={documentsLoading} onDeleted={(id) => setDocuments((items) => items.filter((item) => item.id !== id))} />
              </section>
              <div className="overview-bottom"><span>RETRIVAI WORKS WITH YOUR DOCUMENTS</span><div><span>PDF</span><span>DOCX</span><span>TXT</span></div><Link href="/chat">Ask a question <span>↗</span></Link></div>
            </>
          )}
          {active === "chat" && (
            <>
              <div className="page-heading compact-heading"><div><span className="eyebrow">ASK WITH CONTEXT</span><h1>Your documents, in conversation.</h1><p>Answers are grounded in your indexed library, with source passages attached.</p></div></div>
              <ChatWindow />
            </>
          )}
          {active === "documents" && (
            <>
              <div className="page-heading compact-heading"><div><span className="eyebrow">DOCUMENT MANAGEMENT</span><h1>Your source library.</h1><p>Only you can retrieve or remove the documents in this workspace.</p></div><div className="library-summary"><strong>{readyDocuments.length}</strong><span>ready to search</span></div></div>
              <section className="content-section document-upload-section"><div className="section-heading"><div><span className="eyebrow">ADD TO YOUR LIBRARY</span><h2>Upload a document</h2></div></div><DocumentUpload onUploaded={(document) => setDocuments((items) => [document, ...items.filter((item) => item.id !== document.id)])} /></section>
              <section className="content-section library-section"><div className="section-heading"><div><span className="eyebrow">PRIVATE TO YOUR ACCOUNT</span><h2>All documents <span className="heading-count">{documents.length}</span></h2></div><button className="text-link refresh-link" onClick={() => void loadDocuments()} type="button">Refresh <span>↻</span></button></div><DocumentList documents={documents} loading={documentsLoading} onDeleted={(id) => setDocuments((items) => items.filter((item) => item.id !== id))} /></section>
            </>
          )}
          {active === "architecture" && (
            <>
              <div className="page-heading compact-heading"><div><span className="eyebrow">UNDER THE HOOD</span><h1>From a file to a sourced answer.</h1><p>Two connected paths: one builds a searchable index, the other uses it to answer your question.</p></div></div>
              <section className="architecture-panel panel"><div className="architecture-panel-heading"><div><span className="eyebrow">RETRIVAi SYSTEM MAP</span><h2>A closer look at the pipeline</h2></div><span className="architecture-live"><i /> LIVE COMPONENTS</span></div><ArchitectureDiagram /></section>
              <div className="architecture-note"><span className="note-icon">i</span><p><strong>Grounding has limits.</strong> Retrieval and citations help you inspect the evidence, but they cannot guarantee every generated statement is correct. Open a source passage and verify important details.</p></div>
            </>
          )}
        </main>
        <footer className="app-footer"><span>RETRIVAI © {new Date().getFullYear()}</span><span>RETRIEVE <i>·</i> GROUND <i>·</i> ANSWER</span><Link href="/architecture">How it works <span>↗</span></Link></footer>
      </div>
    </div>
  );
}
