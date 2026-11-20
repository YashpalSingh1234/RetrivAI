"use client";

import { useCallback, useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from "react";
import { api } from "@/lib/api";
import type { ChatMessage, ConversationSummary } from "@/lib/types";
import { SourceCitation } from "@/components/SourceCitation";

type DisplayMessage = ChatMessage & {
  generation_mode?: "llm" | "extractive" | "insufficient_context";
  warning?: string | null;
};

const suggestions = [
  "Give me a short overview of this document",
  "What are the most important concepts?",
  "Find details I should remember",
];

function AnswerText({ text }: { text: string }) {
  const chunks = text.split(/(\[S\d+\])/g);
  return (
    <div className="answer-text">
      {chunks.map((part, index) => /^\[S\d+\]$/.test(part)
        ? <span className="inline-citation" key={`${part}-${index}`}>{part}</span>
        : <span key={index}>{part}</span>)}
    </div>
  );
}

function timestamp(value: string) {
  return new Intl.DateTimeFormat(undefined, { hour: "numeric", minute: "2-digit" }).format(new Date(value));
}

export function ChatWindow() {
  const [messages, setMessages] = useState<DisplayMessage[]>([]);
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [question, setQuestion] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const endRef = useRef<HTMLDivElement>(null);

  const refreshConversations = useCallback(async () => {
    try {
      setConversations(await api.getConversations());
    } catch {
      // An expired session is handled by the app shell; an empty sidebar is fine here.
    }
  }, []);

  useEffect(() => {
    let active = true;
    async function load() {
      try {
        const list = await api.getConversations();
        if (!active) return;
        setConversations(list);
        const saved = window.localStorage.getItem("retrivai-active-conversation");
        if (saved && list.some((item) => item.id === saved)) {
          const detail = await api.getConversation(saved);
          if (active) {
            setConversationId(saved);
            setMessages(detail.messages);
          }
        }
      } catch {
        // The workspace still opens cleanly when there is no prior chat history.
      }
    }
    void load();
    return () => { active = false; };
  }, []);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, busy]);

  async function send(event?: FormEvent<HTMLFormElement>) {
    event?.preventDefault();
    const text = question.trim();
    if (!text || busy) return;
    setQuestion("");
    setError("");
    setBusy(true);
    const userMessage: DisplayMessage = {
      id: `local-${Date.now()}`,
      role: "user",
      content: text,
      sources: [],
      created_at: new Date().toISOString(),
    };
    setMessages((current) => [...current, userMessage]);
    try {
      const result = await api.chat(text, conversationId);
      const nextId = result.conversation_id || conversationId;
      setConversationId(nextId);
      if (nextId) window.localStorage.setItem("retrivai-active-conversation", nextId);
      setMessages((current) => [...current, {
        id: `assistant-${Date.now()}`,
        role: "assistant",
        content: result.answer,
        sources: result.sources,
        created_at: new Date().toISOString(),
        generation_mode: result.generation_mode,
        warning: result.warning,
      }]);
      await refreshConversations();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Your question could not be answered.");
    } finally {
      setBusy(false);
    }
  }

  async function openConversation(id: string) {
    setError("");
    setBusy(true);
    try {
      const detail = await api.getConversation(id);
      setConversationId(id);
      window.localStorage.setItem("retrivai-active-conversation", id);
      setMessages(detail.messages);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Couldn't open this conversation.");
    } finally {
      setBusy(false);
    }
  }

  async function removeConversation(id: string) {
    try {
      await api.deleteConversation(id);
      setConversations((items) => items.filter((item) => item.id !== id));
      if (conversationId === id) startNewConversation();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Couldn't remove this conversation.");
    }
  }

  function startNewConversation() {
    setConversationId(null);
    setMessages([]);
    setError("");
    window.localStorage.removeItem("retrivai-active-conversation");
  }

  function onInputKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      void send();
    }
  }

  return (
    <section className="chat-layout">
      <aside className="chat-history panel">
        <div className="history-topline">
          <div><span className="eyebrow">YOUR THREADS</span><h3>Conversations</h3></div>
          <button className="icon-button add-chat" type="button" onClick={startNewConversation} title="Start a new chat" aria-label="Start a new chat">＋</button>
        </div>
        <div className="conversation-list">
          {conversations.length === 0 && <p className="history-empty">Your questions and answers will appear here.</p>}
          {conversations.map((item) => (
            <div className={`conversation-item ${conversationId === item.id ? "active" : ""}`} key={item.id}>
              <button type="button" onClick={() => void openConversation(item.id)} title={item.title}>
                <span>{item.title}</span><small>{item.message_count} messages</small>
              </button>
              <button className="conversation-delete" type="button" title="Delete conversation" aria-label={`Delete ${item.title}`} onClick={() => void removeConversation(item.id)}>×</button>
            </div>
          ))}
        </div>
        <div className="history-note"><span className="privacy-dot" />Chats are saved to your account</div>
      </aside>

      <div className="chat-main panel">
        <div className="chat-topbar">
          <div><span className="eyebrow">DOCUMENT Q&A</span><h2>{conversationId ? "Keep exploring" : "Ask your documents"}</h2></div>
          <button className="button button-quiet new-chat-button" type="button" onClick={startNewConversation}>＋ New chat</button>
        </div>
        <div className={`message-area ${messages.length === 0 ? "empty" : ""}`} aria-live="polite">
          {messages.length === 0 ? (
            <div className="chat-empty-content">
              <div className="chat-orbit" aria-hidden="true"><span>R</span><i /><b /></div>
              <span className="eyebrow">GROUNDED IN YOUR LIBRARY</span>
              <h3>What would you like to know?</h3>
              <p>Ask a question in plain language. RetrivAI searches your documents and shows the passages behind its answer.</p>
              <div className="suggestion-list">
                {suggestions.map((suggestion) => (
                  <button type="button" key={suggestion} onClick={() => setQuestion(suggestion)}>{suggestion}<span aria-hidden="true">↗</span></button>
                ))}
              </div>
            </div>
          ) : (
            <div className="message-stack">
              {messages.map((message) => (
                <article className={`message ${message.role}`} key={message.id}>
                  <div className="message-avatar">{message.role === "user" ? "You" : "R"}</div>
                  <div className="message-body">
                    <div className="message-meta">
                      <strong>{message.role === "user" ? "You" : "RetrivAI"}</strong>
                      <time>{timestamp(message.created_at)}</time>
                      {message.generation_mode === "extractive" && <span className="mode-tag">EXTRACTIVE</span>}
                    </div>
                    {message.role === "assistant" ? <AnswerText text={message.content} /> : <p>{message.content}</p>}
                    {message.warning && <div className="notice notice-soft">{message.warning}</div>}
                    {message.role === "assistant" && <SourceCitation sources={message.sources} />}
                  </div>
                </article>
              ))}
              {busy && <div className="thinking-row"><span className="thinking-dots"><i /><i /><i /></span><span>Searching your library and preparing an answer…</span></div>}
              <div ref={endRef} />
            </div>
          )}
        </div>
        {error && <div className="inline-error chat-error" role="alert">{error}</div>}
        <form className="composer" onSubmit={(event) => void send(event)}>
          <textarea
            rows={1}
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            onKeyDown={onInputKeyDown}
            placeholder="Ask something about your documents…"
            maxLength={2000}
            aria-label="Ask a question about your documents"
            disabled={busy}
          />
          <div className="composer-bottom">
            <span>Answers use your indexed documents and include source passages.</span>
            <button className="send-button" type="submit" disabled={busy || question.trim().length < 2} aria-label="Send question">{busy ? <span className="spinner" /> : "↑"}</button>
          </div>
        </form>
      </div>
    </section>
  );
}
