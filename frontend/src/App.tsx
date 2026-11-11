import { useCallback, useEffect, useRef, useState } from "react";
import { Menu } from "lucide-react";
import { Dashboard } from "./components/Dashboard";
import { Sidebar, MobileBottomNav, navigation } from "./components/Navigation";
import { TempoLogo } from "./components/TempoLogo";
import { createMockProgress, demoUser, openings } from "./mocks/dashboard";
import type { Page } from "./types";

function currentPage(): Page {
  const hash = window.location.hash.slice(1);
  return navigation.find((item) => item.id === hash)?.id ?? "dashboard";
}
export default function App() {
  const [page, setPage] = useState<Page>(currentPage);
  const [mobileNav, setMobileNav] = useState(false);
  const [progress] = useState(createMockProgress);
  const main = useRef<HTMLElement>(null);
  const closeMenu = useCallback(() => setMobileNav(false), []);
  function navigate(next: Page) {
    window.location.hash = next;
    setMobileNav(false);
  }
  useEffect(() => {
    const update = () => {
      setPage(currentPage());
      window.scrollTo({ top: 0 });
      requestAnimationFrame(() => main.current?.focus());
    };
    window.addEventListener("hashchange", update);
    return () => window.removeEventListener("hashchange", update);
  }, []);
  useEffect(() => {
    document.title = `TEMPO · ${navigation.find((item) => item.id === page)?.label}`;
  }, [page]);
  useEffect(() => {
    const desktop = window.matchMedia("(min-width: 801px)");
    const closeOnDesktop = () => { if (desktop.matches) setMobileNav(false); };
    desktop.addEventListener("change", closeOnDesktop);
    return () => desktop.removeEventListener("change", closeOnDesktop);
  }, []);
  const destination = navigation.find((item) => item.id === page)!;
  return <div className="app-shell">
    <a className="skip-link" href="#main-content" onClick={(event) => { event.preventDefault(); main.current?.focus(); }}>Skip to content</a>
    <Sidebar page={page} onSelect={navigate} username={demoUser.name} open={mobileNav} onClose={closeMenu} />
    <main ref={main} id="main-content" className="main-area" tabIndex={-1} inert={mobileNav}>
      <div className="mobile-topbar"><TempoLogo /><button className="mobile-menu" onClick={() => setMobileNav(true)}
        aria-label="Open menu" aria-expanded={mobileNav} aria-controls="primary-navigation"><Menu /></button></div>
      {page === "dashboard" ? <Dashboard username={demoUser.name} progress={progress} openings={openings}
        onLearn={() => navigate("openings")} onReview={() => navigate("practice")} onPlanner={() => navigate("planner")} />
        : <div className="page"><header className="page-header"><div><p className="eyebrow">COMING LATER</p>
          <h1>{destination.label}</h1><p>This section is planned for a future milestone.</p></div></header>
          <section className="placeholder-card"><destination.icon size={32} aria-hidden="true" />
            <h2>The dashboard is ready to explore.</h2><p>Learning sessions, reviews, planner tools and account settings are not available in this preview.</p>
            <button className="primary-button" onClick={() => navigate("dashboard")}>Back to dashboard</button>
          </section></div>}
    </main>
    <div inert={mobileNav}><MobileBottomNav page={page} onSelect={navigate} /></div>
  </div>;
}
