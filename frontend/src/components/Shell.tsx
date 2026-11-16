import type { ReactNode } from "react";
import { BookOpen, Home, Layers, RotateCcw, Settings, UserRound } from "lucide-react";
import { useApp, type Route } from "../lib/app";
import type { Session } from "../lib/practiceApi";

const NAV = [
  { id: "home", label: "Dashboard", icon: Home },
  { id: "learn", label: "Learning", icon: BookOpen },
  { id: "review", label: "Repeating", icon: RotateCcw },
  { id: "repertoire", label: "Repertoire", icon: Layers },
  { id: "settings", label: "Settings", icon: Settings },
] as const;

export function Shell({ route, session, children }: { route: Route; session: Session | null; children: ReactNode }) {
  const { dueCount, go, account } = useApp();
  const active = route.view === "family" ? "learn"
    : route.view === "lesson" ? (session?.mode === "repeating" ? "review" : "learn") : route.view;
  // The profile icon opens the Profile section of Settings.
  const profileLabel = account ? `${account.name}: open your profile` : "Guest: sign in or create an account";
  const profileIcon = account
    ? <span className="avatar">{account.name.slice(0, 1).toUpperCase()}</span>
    : <span className="avatar"><UserRound size={18} /></span>;
  return <div className="shell">
    <aside className="side" aria-label="Main navigation">
      <div className="brand"><span className="brand-mark" aria-hidden="true">♞</span><div><b>TEMPO</b><small>Chess openings</small></div></div>
      <div className="nav-label">PRACTICE</div>
      {NAV.map(({ id, label, icon: Icon }) => <button key={id} className={`nav ${active === id ? "on" : ""}`}
        aria-current={active === id ? "page" : undefined} onClick={() => go(`#/${id}`)}>
        <Icon size={18} />{label}{id === "review" && dueCount > 0 && <span className="count">{dueCount}</span>}</button>)}
      <div className="side-foot">
        <button className="profile-icon" onClick={() => go("#/settings/profile")} title={profileLabel} aria-label={profileLabel}>
          {profileIcon}</button>
      </div>
    </aside>
    <main className="main" id="main">{children}</main>
    <nav className="bottom-nav" aria-label="Main navigation">
      {NAV.map(({ id, label, icon: Icon }) =>
        <button key={id} className={active === id ? "on" : ""} aria-current={active === id ? "page" : undefined} onClick={() => go(`#/${id}`)}>
          <Icon size={20} />{label}{id === "review" && dueCount > 0 && <span className="dot">{dueCount}</span>}</button>)}
    </nav>
  </div>;
}
