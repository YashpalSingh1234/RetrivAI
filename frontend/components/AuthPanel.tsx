"use client";

import { useState, type FormEvent } from "react";
import { api } from "@/lib/api";
import type { User } from "@/lib/types";

export function AuthPanel({ onAuthenticated }: { onAuthenticated: (user: User) => void }) {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setBusy(true);
    try {
      const user = mode === "login"
        ? await api.login(email, password)
        : await api.register(email, password);
      onAuthenticated(user);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sign in failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="auth-screen">
      <div className="auth-mark"><span className="brand-glyph">R</span> RetrivAI</div>
      <section className="auth-card">
        <div className="eyebrow">YOUR PRIVATE KNOWLEDGE SPACE</div>
        <h1>{mode === "login" ? "Welcome back." : "Make room for better answers."}</h1>
        <p className="muted">Upload the documents you work with. Ask questions and see exactly where each answer came from.</p>
        <form className="auth-form" onSubmit={submit}>
          <label htmlFor="email">Email address</label>
          <input
            id="email"
            type="email"
            autoComplete="email"
            required
            maxLength={254}
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            placeholder="you@example.com"
          />
          <label htmlFor="password">Password</label>
          <input
            id="password"
            type="password"
            autoComplete={mode === "login" ? "current-password" : "new-password"}
            minLength={10}
            maxLength={128}
            required
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            placeholder="At least 10 characters"
          />
          {error && <div className="inline-error" role="alert">{error}</div>}
          <button className="button button-primary auth-submit" disabled={busy}>
            {busy ? "One moment…" : mode === "login" ? "Sign in" : "Create account"}
            <span aria-hidden="true">↗</span>
          </button>
        </form>
        <div className="auth-switch">
          {mode === "login" ? "New to RetrivAI?" : "Already have an account?"}{" "}
          <button type="button" onClick={() => { setError(""); setMode(mode === "login" ? "register" : "login"); }}>
            {mode === "login" ? "Create an account" : "Sign in"}
          </button>
        </div>
        <div className="auth-footnote"><span className="privacy-dot" />Your workspace is isolated to your account.</div>
      </section>
      <div className="auth-side-note">RETRIEVE WITH CONTEXT. ANSWER WITH CONFIDENCE.</div>
    </main>
  );
}
