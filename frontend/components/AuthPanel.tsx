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
  const isLogin = mode === "login";

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setBusy(true);
    try {
      const user = isLogin
        ? await api.login(email, password)
        : await api.register(email, password);
      onAuthenticated(user);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong. Please try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="auth-screen">
      <div className="auth-mark"><span className="brand-glyph" aria-hidden="true">R</span> RetrivAI</div>
      <section className="auth-card" aria-labelledby="auth-title">
        <h1 id="auth-title">{isLogin ? "Sign in" : "Create an account"}</h1>
        <p className="auth-intro">
          {isLogin
            ? "Access your documents and ask questions about them."
            : "Upload documents, ask questions, and see where each answer comes from."}
        </p>
        <form className="auth-form" onSubmit={submit}>
          <div className="auth-field">
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
          </div>
          <div className="auth-field">
            <label htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              autoComplete={isLogin ? "current-password" : "new-password"}
              aria-describedby={isLogin ? undefined : "password-hint"}
              minLength={10}
              maxLength={128}
              required
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
            {!isLogin && <p className="auth-hint" id="password-hint">Use at least 10 characters.</p>}
          </div>
          {error && <div className="inline-error" role="alert">{error}</div>}
          <button type="submit" className="button button-primary auth-submit" disabled={busy}>
            {busy ? "One moment…" : isLogin ? "Sign in" : "Create account"}
          </button>
        </form>
        <div className="auth-switch">
          {isLogin ? "New to RetrivAI?" : "Already have an account?"}{" "}
          <button type="button" onClick={() => { setError(""); setMode(isLogin ? "register" : "login"); }}>
            {isLogin ? "Create an account" : "Sign in"}
          </button>
        </div>
        <div className="auth-footnote"><span className="privacy-dot" aria-hidden="true" />Your workspace is private to your account.</div>
      </section>
    </main>
  );
}
