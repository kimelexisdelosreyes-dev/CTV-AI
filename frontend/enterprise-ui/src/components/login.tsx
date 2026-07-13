"use client";

import { FormEvent, useState } from "react";
import { login } from "@/lib/api";

type Props = { onSuccess: () => void };

export function Login({ onSuccess }: Props) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await login(email, password);
      onSuccess();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Login failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="login-screen">
      <section className="login-card">
        <div className="login-logo">CTV ONE</div>
        <p>Private enterprise intelligence for multimedia teams.</p>
        <form onSubmit={submit}>
          <label>Email</label>
          <input
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            required
          />
          <label>Password</label>
          <input
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
          />
          <button disabled={busy}>{busy ? "Signing in…" : "Sign in"}</button>
          {error && <div className="error">{error}</div>}
        </form>
      </section>
    </main>
  );
}
