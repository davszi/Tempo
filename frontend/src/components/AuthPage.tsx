import { useEffect, useRef, useState, type FormEvent } from "react";
import { Check, Eye, EyeOff } from "lucide-react";
import { googleSignIn, login, register, type Account } from "../lib/auth";

type Mode = "login" | "signup";
type GoogleId = {
  initialize: (options: { client_id: string; callback: (response: { credential: string }) => void }) => void;
  renderButton: (element: HTMLElement, options: Record<string, string | number>) => void;
};
declare global { interface Window { google?: { accounts: { id: GoogleId } } } }

const GOOGLE_SCRIPT = "https://accounts.google.com/gsi/client";
let googleScript: Promise<void> | null = null;
function loadGoogle() {
  googleScript ??= new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = GOOGLE_SCRIPT;
    script.async = true;
    script.onload = () => resolve();
    script.onerror = () => { googleScript = null; reject(new Error("Couldn't load Google sign-in")); };
    document.head.appendChild(script);
  });
  return googleScript;
}

function GoogleIcon() {
  return <svg width="18" height="18" viewBox="0 0 48 48" aria-hidden="true">
    <path fill="#FFC107" d="M43.6 20.5H42V20H24v8h11.3C33.7 32.7 29.2 36 24 36c-6.6 0-12-5.4-12-12s5.4-12 12-12c3.1 0 5.8 1.2 7.9 3.1l5.7-5.7C34 6.1 29.3 4 24 4 12.9 4 4 12.9 4 24s8.9 20 20 20 20-8.9 20-20c0-1.3-.1-2.4-.4-3.5z" />
    <path fill="#FF3D00" d="m6.3 14.7 6.6 4.8C14.7 15.1 19 12 24 12c3.1 0 5.8 1.2 7.9 3.1l5.7-5.7C34 6.1 29.3 4 24 4 16.3 4 9.7 8.3 6.3 14.7z" />
    <path fill="#4CAF50" d="M24 44c5.2 0 9.9-2 13.4-5.2l-6.2-5.2C29.2 35.1 26.7 36 24 36c-5.2 0-9.6-3.3-11.3-7.9l-6.5 5C9.5 39.6 16.2 44 24 44z" />
    <path fill="#1976D2" d="M43.6 20.5H42V20H24v8h11.3c-.8 2.2-2.2 4.2-4.1 5.6l6.2 5.2C37 39.2 44 34 44 24c0-1.3-.1-2.4-.4-3.5z" />
  </svg>;
}

/** Sign-in and create-account pages: one centred card in the app's current theme. */
export function AuthPage({ mode, googleClientId, onSignedIn, go }: {
  mode: Mode; googleClientId: string | null; onSignedIn: (user: Account) => void; go: (hash: string) => void;
}) {
  const signup = mode === "signup";
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [show, setShow] = useState(false);
  const [error, setError] = useState("");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const googleButton = useRef<HTMLDivElement>(null);

  useEffect(() => { setError(""); setNote(""); setPassword(""); setConfirm(""); }, [mode]);

  // With a client ID, Google draws its own button; the backend checks the token it returns.
  useEffect(() => {
    if (!googleClientId || !googleButton.current) return;
    let cancelled = false;
    loadGoogle().then(() => {
      if (cancelled || !window.google || !googleButton.current) return;
      window.google.accounts.id.initialize({
        client_id: googleClientId,
        callback: ({ credential }) => void finish(() => googleSignIn(credential)),
      });
      googleButton.current.innerHTML = "";
      window.google.accounts.id.renderButton(googleButton.current, {
        theme: "outline", size: "large", shape: "rectangular", width: 320,
        text: signup ? "signup_with" : "continue_with",
      });
    }).catch((failure: Error) => setError(failure.message));
    return () => { cancelled = true; };
  }, [googleClientId, signup]); // eslint-disable-line react-hooks/exhaustive-deps

  async function finish(request: () => Promise<{ user: Account }>) {
    setBusy(true);
    setError("");
    try {
      const { user } = await request();
      onSignedIn(user);
    } catch (failure) {
      setError((failure as Error).message);
    } finally {
      setBusy(false);
    }
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    setNote("");
    if (signup) {
      if (!name.trim()) return setError("Enter your name");
      if (password.length < 8) return setError("Use at least 8 characters for your password");
      if (password !== confirm) return setError("Passwords don't match");
      void finish(() => register(name, email, password));
    } else {
      if (!email || !password) return setError("Enter your email and password");
      void finish(() => login(email, password));
    }
  }

  const matches = confirm.length > 0 && confirm === password;
  return <div className="auth">
    <div className="auth-box">
    <button type="button" className="auth-brand" onClick={() => go("#/home")}>
      <span className="brand-mark" aria-hidden="true">♞</span><span><b>TEMPO</b><small>Chess openings</small></span></button>
    <section className="card auth-card" aria-labelledby="auth-title">
      <h2 id="auth-title">{signup ? "Create your account" : "Welcome back"}</h2>
      <p className="auth-sub">{signup ? "Save your repertoire and review on any device." : "Sign in to keep your openings fresh."}</p>
      {googleClientId
        ? <div ref={googleButton} className="auth-google-slot" />
        : <button type="button" className="btn ghost full auth-google" onClick={() => setNote("Google sign-in isn't set up yet. Your team needs to add a Google Client ID to the backend.")}>
          <GoogleIcon />{signup ? "Sign up with Google" : "Continue with Google"}</button>}
      <div className="auth-or">or</div>
      <form onSubmit={submit} noValidate>
        {signup && <label className="auth-field">Name<input value={name} onChange={(e) => setName(e.target.value)} autoComplete="name" placeholder="Priya" /></label>}
        <label className="auth-field">Email<input type="email" value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="email" placeholder="name@example.com" /></label>
        <label className="auth-field">
          <span className="auth-label-row">Password{!signup && <button type="button" className="auth-link" onClick={() => go("#/forgot-password")}>Forgot password?</button>}</span>
          <span className="auth-input">
            <input type={show ? "text" : "password"} value={password} onChange={(e) => setPassword(e.target.value)} autoComplete={signup ? "new-password" : "current-password"} placeholder="••••••••" />
            <button type="button" className="auth-eye" onClick={() => setShow(!show)} aria-label={show ? "Hide password" : "Show password"}>{show ? <EyeOff size={16} /> : <Eye size={16} />}</button>
          </span>
        </label>
        {signup && <label className="auth-field">Confirm password
          <span className="auth-input">
            <input type={show ? "text" : "password"} value={confirm} onChange={(e) => setConfirm(e.target.value)} autoComplete="new-password" placeholder="••••••••" />
            {matches && <span className="auth-ok" aria-label="Passwords match"><Check size={16} /></span>}
          </span>
        </label>}
        {signup && <p className="auth-hint">At least 8 characters. Both passwords must match.</p>}
        {error && <p className="auth-error" role="alert">{error}</p>}
        {note && <p className="auth-note" role="status">{note}</p>}
        <button type="submit" className="btn primary full auth-submit" disabled={busy}>{busy ? "Please wait…" : signup ? "Create account" : "Sign in"}</button>
      </form>
      <p className="auth-foot">{signup
        ? <>Already have an account? <button type="button" className="auth-link" onClick={() => go("#/login")}>Sign in</button></>
        : <>New to TEMPO? <button type="button" className="auth-link" onClick={() => go("#/signup")}>Create an account</button></>}</p>
      <p className="auth-foot"><button type="button" className="auth-link muted-link" onClick={() => go("#/home")}>Continue as a guest</button></p>
    </section>
    </div>
  </div>;
}
