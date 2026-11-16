import { useEffect, useRef, useState, type FormEvent } from "react";
import { KeyRound, LogIn, LogOut, Pencil, Trash2, UserPlus, UserRound } from "lucide-react";
import { useApp } from "../lib/app";
import { changePassword, deleteAccount, updateProfile } from "../lib/auth";

/** The Profile section of Settings: details, password, sign out and delete account. */
export function ProfileSettings({ startEditing }: { startEditing: boolean }) {
  const { account, signOut, accountChanged, accountDeleted, showToast, go } = useApp();
  const section = useRef<HTMLElement>(null);
  const [editing, setEditing] = useState(startEditing);
  const [name, setName] = useState(account?.name ?? "");
  const [email, setEmail] = useState(account?.email ?? "");
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [repeat, setRepeat] = useState("");
  const [deleting, setDeleting] = useState(false);
  const [confirmValue, setConfirmValue] = useState("");
  const [busy, setBusy] = useState("");
  const [error, setError] = useState<{ where: string; text: string } | null>(null);

  useEffect(() => { if (startEditing) section.current?.scrollIntoView({ block: "start" }); }, [startEditing]);
  useEffect(() => { setName(account?.name ?? ""); setEmail(account?.email ?? ""); }, [account]);

  async function run(where: string, action: () => Promise<void>) {
    setBusy(where);
    setError(null);
    try { await action(); } catch (failure) { setError({ where, text: (failure as Error).message }); } finally { setBusy(""); }
  }
  const errorFor = (where: string) => error?.where === where ? <p className="form-error" role="alert">{error.text}</p> : null;

  if (!account) {
    return <section ref={section} className="card profile-card" id="profile" aria-labelledby="profile-title">
      <div className="profile-head">
        <span className="avatar big"><UserRound size={26} /></span>
        <div className="grow"><h2 id="profile-title">You're using TEMPO as a guest</h2>
          <p className="muted small">Your progress stays on this device. Create an account to keep a separate repertoire you can sign in to.</p></div>
      </div>
      <div className="row profile-actions">
        <button className="btn primary" onClick={() => go("#/login")}><LogIn size={16} /> Sign in</button>
        <button className="btn ghost" onClick={() => go("#/signup")}><UserPlus size={16} /> Create account</button>
      </div>
    </section>;
  }

  function saveProfile(event: FormEvent) {
    event.preventDefault();
    void run("profile", async () => {
      const { user } = await updateProfile(name, email);
      accountChanged(user);
      setEditing(false);
      showToast("Profile saved");
    });
  }
  function savePassword(event: FormEvent) {
    event.preventDefault();
    if (next.length < 8) return setError({ where: "password", text: "Use at least 8 characters for your new password" });
    if (next !== repeat) return setError({ where: "password", text: "New passwords don't match" });
    void run("password", async () => {
      const { user } = await changePassword(current, next);
      accountChanged(user);
      setCurrent(""); setNext(""); setRepeat("");
      showToast(account?.has_password ? "Password changed" : "Password set");
    });
  }
  function removeAccount(event: FormEvent) {
    event.preventDefault();
    void run("delete", async () => {
      await deleteAccount(account?.has_password ? confirmValue : "", account?.has_password ? "" : confirmValue);
      await accountDeleted();
    });
  }

  return <section ref={section} className="card profile-card" id="profile" aria-labelledby="profile-title">
    <div className="profile-head">
      <span className="avatar big">{account.name.slice(0, 1).toUpperCase()}</span>
      <div className="grow"><h2 id="profile-title">{account.name}</h2>
        <p className="muted small">{account.email}{account.google ? " · Google" : ""}</p></div>
      {!editing && <button className="btn sm ghost" onClick={() => setEditing(true)}><Pencil size={15} /> Edit profile</button>}
    </div>

    {editing && <form className="profile-form" onSubmit={saveProfile}>
      <label className="field">Name<input value={name} onChange={(e) => setName(e.target.value)} autoComplete="name" /></label>
      <label className="field">Email<input type="email" value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="email" /></label>
      {errorFor("profile")}
      <div className="row profile-actions">
        <button className="btn primary" disabled={busy === "profile"}>{busy === "profile" ? "Saving…" : "Save changes"}</button>
        <button type="button" className="btn ghost" onClick={() => { setEditing(false); setName(account.name); setEmail(account.email ?? ""); setError(null); }}>Cancel</button>
      </div>
    </form>}

    <hr className="divider" />
    <h3 className="profile-sub"><KeyRound size={16} /> {account.has_password ? "Change password" : "Set a password"}</h3>
    <form className="profile-form" onSubmit={savePassword}>
      {account.has_password && <label className="field">Current password<input type="password" value={current} onChange={(e) => setCurrent(e.target.value)} autoComplete="current-password" /></label>}
      <label className="field">New password<input type="password" value={next} onChange={(e) => setNext(e.target.value)} autoComplete="new-password" /></label>
      <label className="field">Repeat new password<input type="password" value={repeat} onChange={(e) => setRepeat(e.target.value)} autoComplete="new-password" /></label>
      {errorFor("password")}
      <div className="row profile-actions"><button className="btn ghost" disabled={busy === "password"}>{busy === "password" ? "Saving…" : account.has_password ? "Change password" : "Set password"}</button></div>
    </form>

    <hr className="divider" />
    <div className="row profile-actions">
      <button className="btn ghost" onClick={() => void signOut()}><LogOut size={16} /> Sign out</button>
      {!deleting && <button className="btn ghost danger" onClick={() => setDeleting(true)}><Trash2 size={16} /> Delete account</button>}
    </div>
    {deleting && <form className="danger-zone" onSubmit={removeAccount}>
      <p><b>Delete your account?</b> This removes your account, your repertoire and your review history for good. It can't be undone.</p>
      <label className="field">{account.has_password ? "Enter your password to confirm" : "Type DELETE to confirm"}
        <input type={account.has_password ? "password" : "text"} value={confirmValue} onChange={(e) => setConfirmValue(e.target.value)}
          autoComplete={account.has_password ? "current-password" : "off"} /></label>
      {errorFor("delete")}
      <div className="row profile-actions">
        <button className="btn danger-solid" disabled={busy === "delete" || !confirmValue}>{busy === "delete" ? "Deleting…" : "Delete my account"}</button>
        <button type="button" className="btn ghost" onClick={() => { setDeleting(false); setConfirmValue(""); setError(null); }}>Keep my account</button>
      </div>
    </form>}
  </section>;
}
