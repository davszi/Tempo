import { useEffect, useRef } from "react";
import { BookOpen, Home, LogOut, RotateCcw, Settings, X } from "lucide-react";
import { TempoLogo } from "./TempoLogo";
import type { Page } from "../types";

export const pages = [
  { id: "dashboard", label: "Dashboard", short: "Home", icon: Home },
  { id: "openings", label: "Learning mode", short: "Learn", icon: BookOpen },
  { id: "practice", label: "Repeating & reviews", short: "Review", icon: RotateCcw },
  { id: "settings", label: "Settings", short: "Settings", icon: Settings },
] as const;

export const navigation = pages.filter((item) => item.id !== "settings");

export function ProfileButton({ username, active, onClick }: {
  username: string; active: boolean; onClick: () => void;
}) {
  return <button type="button" className={`avatar profile-button ${active ? "profile-active" : ""}`}
    aria-label="Open settings" aria-current={active ? "page" : undefined} title="Open settings" onClick={onClick}>
    {username.slice(0, 1).toUpperCase()}
  </button>;
}

type NavigationProps = { page: Page; onSelect: (page: Page) => void };
export function Sidebar({ page, onSelect, username, open, onClose }: NavigationProps & {
  username: string; open: boolean; onClose: () => void;
}) {
  const sidebar = useRef<HTMLElement>(null);
  useEffect(() => {
    if (!open) return;
    const previous = document.activeElement as HTMLElement | null;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const controls = () => Array.from(sidebar.current?.querySelectorAll<HTMLButtonElement>("button:not(:disabled)") ?? []);
    controls()[0]?.focus();
    function handleKey(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
      if (event.key !== "Tab") return;
      const buttons = controls();
      const first = buttons[0], last = buttons[buttons.length - 1];
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus(); }
      if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus(); }
    }
    document.addEventListener("keydown", handleKey);
    return () => {
      document.body.style.overflow = previousOverflow;
      document.removeEventListener("keydown", handleKey);
      previous?.focus();
    };
  }, [open, onClose]);
  return <>
    {open && <button className="sidebar-overlay" onClick={onClose} aria-label="Close menu" tabIndex={-1} />}
    <aside ref={sidebar} id="primary-navigation" className={`sidebar ${open ? "sidebar-open" : ""}`}
      role={open ? "dialog" : undefined} aria-modal={open || undefined} aria-label="Main navigation">
      <div className="sidebar-top"><TempoLogo /><button className="mobile-close" onClick={onClose} aria-label="Close menu"><X /></button></div>
      <nav aria-label="Main"><p className="nav-caption">LEARN</p>
        {navigation.map(({ id, label, icon: Icon }) => <button key={id} className={page === id ? "active" : ""}
          aria-current={page === id ? "page" : undefined} onClick={() => { onSelect(id); onClose(); }}>
          <Icon size={20} strokeWidth={1.8} />{label}
        </button>)}
      </nav>
      <div className="sidebar-user"><ProfileButton username={username} active={page === "settings"}
        onClick={() => { onSelect("settings"); onClose(); }} />
        <div><b>{username}</b><small>Demo student</small></div>
        <button disabled aria-label="Log out unavailable in demo" title="Demo only — no account is signed in"><LogOut size={19} /></button>
      </div>
    </aside>
  </>;
}
export function MobileBottomNav({ page, onSelect }: NavigationProps) {
  return <nav className="mobile-bottom-nav" aria-label="Mobile navigation">
    {navigation.map(({ id, short, icon: Icon }) => <button type="button" key={id}
      className={page === id ? "active" : ""} aria-current={page === id ? "page" : undefined} onClick={() => onSelect(id)}>
      <Icon size={20} strokeWidth={page === id ? 2.3 : 1.8} /><span>{short}</span>
    </button>)}
  </nav>;
}
