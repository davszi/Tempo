import { useCallback, useEffect, useMemo, useState } from "react";
import { buildFamilies, variantMoves } from "./lib/catalog";
import { AppearanceContext, loadAppearance, storeAppearance, type Appearance } from "./lib/appearance";
import { practiceRequest, type OpeningLine, type Repertoire, type ReviewStart, type Session } from "./lib/practiceApi";
import { clearProgress, useProgress } from "./lib/progress";
import { isDue } from "./lib/memory";
import { AppContext, type AppData, type Route } from "./lib/app";
import { Shell } from "./components/Shell";
import { Toast } from "./components/common";
import { DashboardPage } from "./components/DashboardPage";
import { LearnPage } from "./components/LearnPage";
import { FamilyPage } from "./components/FamilyPage";
import { LessonPage } from "./components/LessonPage";
import { ReviewPage } from "./components/ReviewPage";
import { RepertoirePage } from "./components/RepertoirePage";
import { SettingsPage } from "./components/SettingsPage";

function readRoute(): Route {
  const [view, ...rest] = window.location.hash.replace(/^#\/?/, "").split("/");
  const arg = rest.length ? decodeURIComponent(rest.join("/")) : undefined;
  const known = ["home", "learn", "family", "lesson", "review", "repertoire", "settings"] as const;
  return { view: known.find((name) => name === view) ?? "home", arg };
}
const titles: Record<Route["view"], string> = {
  home: "Dashboard", learn: "Learning", family: "Learning", lesson: "Lesson", review: "Repeating", repertoire: "Repertoire", settings: "Settings",
};

export default function App() {
  const [route, setRoute] = useState(readRoute);
  const [appearance, setAppearance] = useState<Appearance>(loadAppearance);
  const [catalog, setCatalog] = useState<OpeningLine[]>([]);
  const [repertoire, setRepertoire] = useState<Repertoire | null>(null);
  const [loadError, setLoadError] = useState("");
  const [loadVersion, setLoadVersion] = useState(0);
  const [session, setSession] = useState<Session | null>(null);
  const [toast, setToast] = useState("");
  const [now, setNow] = useState(Date.now);
  const progress = useProgress();

  const families = useMemo(() => buildFamilies(catalog), [catalog]);
  const variants = useMemo(() => variantMoves(catalog), [catalog]);
  const lineById = useMemo(() => new Map(catalog.map((line) => [line.line_id, line])), [catalog]);

  useEffect(() => {
    const update = () => { setRoute(readRoute()); window.scrollTo({ top: 0 }); };
    window.addEventListener("hashchange", update);
    return () => window.removeEventListener("hashchange", update);
  }, []);
  useEffect(() => { document.title = `TEMPO · ${titles[route.view]}`; }, [route.view]);
  useEffect(() => {
    document.documentElement.dataset.theme = appearance.theme;
    storeAppearance(appearance);
  }, [appearance]);
  useEffect(() => { const timer = window.setInterval(() => setNow(Date.now()), 60_000); return () => window.clearInterval(timer); }, []);

  const refreshRepertoire = useCallback(async () => {
    try {
      setRepertoire(await practiceRequest<Repertoire>("repertoire"));
      setNow(Date.now());
    } catch (failure) { setLoadError((failure as Error).message); }
  }, []);

  useEffect(() => {
    const request = new AbortController();
    setLoadError("");
    practiceRequest<OpeningLine[]>("catalog", {}, request.signal)
      .then((lines) => { if (!request.signal.aborted) setCatalog(lines); })
      .catch((failure: Error) => { if (!request.signal.aborted) setLoadError(failure.message); });
    void refreshRepertoire();
    return () => request.abort();
  }, [loadVersion, refreshRepertoire]);

  // Recall falls as time passes, so fetch fresh numbers whenever a memory view opens.
  useEffect(() => {
    if (["home", "review", "repertoire"].includes(route.view)) void refreshRepertoire();
  }, [route.view, refreshRepertoire]);

  const go = useCallback((hash: string) => {
    if (window.location.hash === hash) setRoute(readRoute());
    else window.location.hash = hash;
  }, []);

  const showToast = useCallback((text: string) => {
    setToast(text);
    window.setTimeout(() => setToast((current) => (current === text ? "" : current)), 2800);
  }, []);

  const startLearning = useCallback(async (lineId: number, { restart = false } = {}) => {
    const line = lineById.get(lineId);
    if (!line) return;
    const side = line.family_side;          // every opening is learned from its family's side
    const saved = progress[lineId];
    if (restart) clearProgress(lineId);
    const resumeAt = !restart && saved && saved.side === side ? saved.ply : 0;
    try {
      const started = await practiceRequest<Session>("learning", { line_id: lineId, side, ...(resumeAt ? { resume_at: resumeAt } : {}) });
      setSession(started);
      go("#/lesson");
    } catch (failure) {
      if (resumeAt) { clearProgress(lineId); showToast("The saved lesson could not be resumed, so it starts again."); }
      else showToast((failure as Error).message);
    }
  }, [lineById, progress, go, showToast]);

  const startReview = useCallback(async (lineId?: number) => {
    try {
      let started: ReviewStart = lineId != null
        ? await practiceRequest<Session>("review/line", { line_id: lineId })
        : await practiceRequest<ReviewStart>("review");
      if (started.status === "learn_first") { showToast("Learn a line first. It joins your repertoire straight away."); go("#/learn"); return; }
      if (started.status === "none_due") { showToast("Nothing is due right now. Pick any line to practise early."); go("#/review"); return; }
      if (started.status === "choose_side") {
        // The planner picked the line; play it from its opening family's side.
        const side = lineById.get(started.line_id)?.family_side ?? "white";
        started = await practiceRequest<Session>("review/side", { session_id: started.session_id, side });
      }
      setSession(started as Session);
      go("#/lesson");
    } catch (failure) { showToast((failure as Error).message); }
  }, [lineById, go, showToast]);

  const markLearned = useCallback((lineId: number) => {
    setCatalog((lines) => lines.map((line) => (line.line_id === lineId ? { ...line, learned: true } : line)));
  }, []);

  const dueCount = repertoire ? repertoire.lines.filter((line) => isDue(line, now)).length : 0;
  const data: AppData = {
    catalog, families, variants, lineById, repertoire, progress, now, go, showToast,
    startLearning, startReview, refreshRepertoire, markLearned, dueCount,
  };

  let page;
  switch (route.view) {
    case "learn": page = <LearnPage />; break;
    case "family": page = <FamilyPage name={route.arg ?? ""} />; break;
    case "lesson": page = session ? <LessonPage key={session.session_id} initial={session} onExit={(hash) => { setSession(null); go(hash); }} />
      : <LearnPage />; break;
    case "review": page = <ReviewPage />; break;
    case "repertoire": page = <RepertoirePage />; break;
    case "settings": page = <SettingsPage appearance={appearance} onChange={setAppearance} />; break;
    default: page = <DashboardPage />;
  }

  return <AppearanceContext.Provider value={appearance}>
    <AppContext.Provider value={data}>
      <Shell route={route} session={session}>
        {loadError && <div className="banner" role="alert">
          <b>{loadError}</b>
          <span>Start the backend with <code>python -m backend.web</code> in the project folder, then retry.</span>
          <button className="btn sm ghost" onClick={() => setLoadVersion((v) => v + 1)}>Retry</button>
        </div>}
        {page}
      </Shell>
      <Toast text={toast} />
    </AppContext.Provider>
  </AppearanceContext.Provider>;
}
