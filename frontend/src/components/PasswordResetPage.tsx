import { useState, type FormEvent } from "react";
import { requestPasswordReset, resetPassword } from "../lib/auth";

export function PasswordResetPage({ reset, token, go, onReset }: {
  reset: boolean; token?: string; go: (hash: string) => void; onReset: () => void;
}) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [busy, setBusy] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState("");
  const validLink = !reset || /^[A-Za-z0-9_-]{43}$/.test(token ?? "");

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError("");
    if (reset && password !== confirm) { setError("Passwords don't match."); return; }
    setBusy(true);
    try {
      if (reset) {
        await resetPassword(token ?? "", password);
        onReset();
      } else {
        await requestPasswordReset(email);
        setSent(true);
      }
    } catch (failure) {
      setError((failure as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return <div className="auth"><div className="auth-box">
    <section className="card auth-card" aria-labelledby="reset-title">
      <h2 id="reset-title">{reset ? "Set a new password" : "Forgot password?"}</h2>
      {!validLink ? <p className="auth-error" role="alert">This reset link is invalid. Request a new one.</p>
        : sent ? <p className="auth-note" role="status">If this address has a password account, you’ll receive a reset link.</p>
        : <form onSubmit={submit}>
          {reset ? <>
            <label className="auth-field">New password<input type="password" autoComplete="new-password" minLength={8} maxLength={200} required value={password} onChange={(event) => setPassword(event.target.value)} /></label>
            <label className="auth-field">Confirm new password<input type="password" autoComplete="new-password" required value={confirm} onChange={(event) => setConfirm(event.target.value)} /></label>
            <p className="auth-hint">Use at least 8 characters.</p>
          </> : <label className="auth-field">Account email<input type="email" autoComplete="email" maxLength={254} required value={email} onChange={(event) => setEmail(event.target.value)} /></label>}
          {error && <p className="auth-error" role="alert">{error}</p>}
          <button className="btn primary full auth-submit" disabled={busy}>{busy ? "Please wait." : reset ? "Set new password" : "Send reset link"}</button>
        </form>}
      {reset && <p className="auth-foot"><button type="button" className="auth-link" onClick={() => go("#/forgot-password")}>Request a new link</button></p>}
      <p className="auth-foot"><button type="button" className="auth-link" onClick={() => go("#/login")}>Back to sign in</button></p>
    </section>
  </div></div>;
}
