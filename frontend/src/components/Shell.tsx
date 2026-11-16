import type { ReactNode } from "react";
import { BookOpen, Home, Layers, LogIn, LogOut, Palette, RotateCcw, SlidersHorizontal } from "lucide-react";
import { useApp, type Route } from "../lib/app";
import type { Session } from "../lib/practiceApi";

const NAV = [
  { id: "home", label: "Dashboard", icon: Home },
  { id: "learn", label: "Learning", icon: BookOpen },
  { id: "review", label: "Repeating", icon: RotateCcw },
  { id: "repertoire", label: "Repertoire", icon: Layers },
] as const;

export function Shell({ route, session, children }: { route: Route; session: Session | null; children: ReactNode }) {
  const { dueCount, go, account, signOut } = useApp();
  const active = route.view === "family" ? "learn"
    : route.view === "lesson" ? (session?.mode === "repeating" ? "review" : "learn") : route.view;
  return <div className="shell">
    <aside className="side" aria-label="Main navigation">
      <div className="brand"><span className="brand-mark" aria-hidden="true">♞</span><div><b>TEMPO</b><small>Chess openings</small></div></div>
      <div className="nav-label">PRACTICE</div>
      {NAV.map(({ id, label, icon: Icon }) => <button key={id} className={`nav ${active === id ? "on" : ""}`}
        aria-current={active === id ? "page" : undefined} onClick={() => go(`#/${id}`)}>
        <Icon size={18} />{label}{id === "review" && dueCount > 0 && <span className="count">{dueCount}</span>}</button>)}
      <div className="side-foot">
        <button className="profile" onClick={() => go("#/settings")}><span className="avatar"><Palette size={18} /></span>
          <span><b>Settings</b><small>Themes &amp; pieces</small></span></button>
        <AccountBox />
      </div>
    </aside>
    <main className="main" id="main">{route.view === "settings" && <div className="account-mobile"><AccountBox /></div>}{children}</main>
    <nav className="bottom-nav" aria-label="Main navigation">
      {[...NAV, { id: "settings", label: "Settings", icon: SlidersHorizontal } as const].map(({ id, label, icon: Icon }) =>
        <button key={id} className={active === id ? "on" : ""} aria-current={active === id ? "page" : undefined} onClick={() => go(`#/${id}`)}>
          <Icon size={20} />{label}{id === "review" && dueCount > 0 && <span className="dot">{dueCount}</span>}</button>)}
    </nav>
  </div>;

  function AccountBox() {
    return account
      ? <div className="account-box"><span className="avatar">{account.name.slice(0, 1).toUpperCase()}</span>
        <span className="account-name"><b>{account.name}</b><small>{account.email}</small></span>
        <button className="btn sm ghost" onClick={() => void signOut()} title="Sign out"><LogOut size={15} /> Sign out</button></div>
      : <div className="account-box"><span className="account-name"><b>Guest</b><small>Progress stays on this device</small></span>
        <button className="btn sm primary" onClick={() => go("#/login")}><LogIn size={15} /> Sign in</button></div>;
  }
}
