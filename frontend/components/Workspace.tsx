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
  { href: "/chat", key: "chat", label: "Chat", icon: "↗" },
  { href: "/documents", key: "documents", label: "Documents", icon: "▤" },
  { href: "/architecture", key: "architecture", label: "How it works", icon: "⌘" },
];

function titleFor(tab: WorkspaceTab) {
  return ({ overview: "Overview", chat: "Chat", documents: "Documents", architecture: "How it works" })[tab];
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
        <div className="workspace-switch"><span className="workspace-avatar">{user.email.slice(0, 1).toUpperCase()}</span><span><strong>Your workspace</strong><small>Private library</small></span></div>
        <nav className="side-nav" aria-label="Main navigation">
          {navItems.map((item) => (
            <Link className={active === item.key ? "active" : ""} href={item.href} key={item.key} aria-current={active === item.key ? "page" : undefined}>
              <span className="nav-icon" aria-hidden="true">{item.icon}</span><span>{item.label}</span>{item.key === "documents" && documents.length > 0 && <span className="nav-count" aria-hidden="true">{documents.length}</span>}
            </Link>
          ))}
        </nav>
        <div className="sidebar-spacer" />
        <div className="sidebar-help"><span className="help-icon">?</span><span><strong>Sources</strong><small>Open a source in chat to read the original text.</small></span></div>
        <div className="sidebar-user">
          <div className="user-avatar">{user.email.slice(0, 1).toUpperCase()}</div>
          <div className="user-details" title={user.email}><strong>{user.email.split("@")[0]}</strong><small>{user.email}</small></div>
          <button type="button" className="signout-button" onClick={() => void signOut()}>Sign out</button>
        </div>
      </aside>

      <div className="main-column">
        <header className="topbar">
          <div className="breadcrumb"><span>Workspace</span><i>/</i><strong>{titleFor(active)}</strong></div>
          <div className="topbar-right">
            <span className="backend-indicator"><i />Connected</span>
            <span className={`model-indicator ${health?.llm_configured ? "configured" : "extractive"}`}>
              <i />{health?.llm_configured ? "AI answers" : "Source excerpts"}
            </span>
          </div>
        </header>
        {startupError && <div className="workspace-warning" role="alert">{startupError}</div>}
        <main className={`page-content page-${active}`}>
          {active === "overview" && (
            <>
              <div className="page-heading"><div><h1>Workspace overview</h1><p>Upload documents, then ask questions about their contents.</p></div><Link className="button button-primary" href="/chat">Open chat <span>↗</span></Link></div>
              <section className="overview-hero">
                <div className="hero-grid-mark" aria-hidden="true"><span /><span /><span /><span /><span /><span /><span /><span /><span /></div>
                <div className="hero-copy"><h2>Find answers in your documents</h2><p>RetrivAI searches your files and shows the passages behind each answer.</p><Link href="/architecture" className="hero-link">See how it works <span>↗</span></Link></div>
                <div className="hero-orb" aria-hidden="true"><div className="orb-ring ring-one" /><div className="orb-ring ring-two" /><div className="orb-center">R</div><span className="orb-dot dot-one" /><span className="orb-dot dot-two" /><span className="orb-dot dot-three" /></div>
              </section>
              <section className="stats-grid" aria-label="Workspace overview">
                <div className="stat-card"><span className="stat-label">Documents</span><div className="stat-value">{readyDocuments.length}<span className="stat-icon">▤</span></div><span className="stat-note">Ready to search</span></div>
                <div className="stat-card"><span className="stat-label">Passages</span><div className="stat-value">{passageCount.toLocaleString()}<span className="stat-icon mint">⌕</span></div><span className="stat-note">Searchable sections of text</span></div>
                <div className="stat-card"><span className="stat-label">Answer mode</span><div className="stat-value mode-value">{health?.llm_configured ? "AI answers" : "Source excerpts"}<span className="stat-icon violet">✳</span></div><span className="stat-note">{health?.llm_configured ? "Uses passages from your files" : "Quotes relevant passages"}</span></div>
              </section>
              <section className="content-section">
                <div className="section-heading"><div><h2>Add a document</h2></div></div>
                <DocumentUpload onUploaded={(document) => { setDocuments((items) => [document, ...items.filter((item) => item.id !== document.id)]); }} />
              </section>
              <section className="content-section library-section">
                <div className="section-heading"><div><h2>Recent documents <span className="heading-count">{documents.length}</span></h2></div><Link href="/documents" className="text-link">View library <span>→</span></Link></div>
                <DocumentList documents={documents.slice(0, 5)} loading={documentsLoading} onDeleted={(id) => setDocuments((items) => items.filter((item) => item.id !== id))} />
              </section>
            </>
          )}
          {active === "chat" && (
            <>
              <div className="page-heading compact-heading"><div><h1>Ask your documents</h1><p>Ask a question and open the sources to read the original passages.</p></div></div>
              <ChatWindow />
            </>
          )}
          {active === "documents" && (
            <>
              <div className="page-heading compact-heading"><div><h1>Documents</h1><p>Upload and manage the files RetrivAI can search.</p></div><div className="library-summary"><strong>{readyDocuments.length}</strong><span>ready to search</span></div></div>
              <section className="content-section document-upload-section"><div className="section-heading"><div><h2>Upload a document</h2></div></div><DocumentUpload onUploaded={(document) => setDocuments((items) => [document, ...items.filter((item) => item.id !== document.id)])} /></section>
              <section className="content-section library-section"><div className="section-heading"><div><h2>All documents <span className="heading-count">{documents.length}</span></h2></div><button className="text-link" onClick={() => void loadDocuments()} type="button">Refresh <span>↻</span></button></div><DocumentList documents={documents} loading={documentsLoading} onDeleted={(id) => setDocuments((items) => items.filter((item) => item.id !== id))} /></section>
            </>
          )}
          {active === "architecture" && (
            <>
              <div className="page-heading compact-heading"><div><h1>How RetrivAI works</h1><p>See how a file becomes searchable and how RetrivAI finds passages to answer a question.</p></div></div>
              <section className="architecture-panel panel"><ArchitectureDiagram /></section>
              <div className="architecture-note"><span className="note-icon">i</span><p>Open the source passages to verify important details in an answer.</p></div>
            </>
          )}
        </main>
        <footer className="app-footer"><span>RetrivAI © {new Date().getFullYear()}</span><Link href="/architecture">How it works <span>↗</span></Link></footer>
      </div>
    </div>
  );
}
