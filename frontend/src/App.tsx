import { useCallback, useEffect, useMemo, useState } from "react";
import { allOpeningTypes, buildFamilies, variantMoves, type OpeningSort, type OpeningType } from "./lib/catalog";
import { AppearanceContext, loadAppearance, storeAppearance, type Appearance } from "./lib/appearance";
import { practiceRequest, type OpeningLine, type Repertoire, type ReviewStart, type Session } from "./lib/practiceApi";
import { clearProgress, saveProgress, useProgress } from "./lib/progress";
import { isDue } from "./lib/memory";
import { AppContext, learningSideKey, type AppData, type LearningSide, type Route } from "./lib/app";
import { Shell } from "./components/Shell";
import { Toast } from "./components/common";
import { DashboardPage } from "./components/DashboardPage";
import { LearnPage } from "./components/LearnPage";
import { FamilyPage } from "./components/FamilyPage";
import { LessonPage } from "./components/LessonPage";
import { ReviewPage } from "./components/ReviewPage";
import { RepertoirePage } from "./components/RepertoirePage";
import { SettingsPage } from "./components/SettingsPage";
import { AuthPage } from "./components/AuthPage";
import { ProfileSettings } from "./components/ProfileSettings";
import { fetchAuthState, logout, rememberAccount, type Account } from "./lib/auth";

function readRoute(): Route {
  const [view, ...rest] = window.location.hash.replace(/^#\/?/, "").split("/");
  const arg = rest.length ? decodeURIComponent(rest.join("/")) : undefined;
  const known = ["home", "learn", "family", "lesson", "review", "repertoire", "settings", "login", "signup"] as const;
  return { view: known.find((name) => name === view) ?? "home", arg };
}
const titles: Record<Route["view"], string> = {
  home: "Dashboard", learn: "Learning", family: "Learning", lesson: "Lesson", review: "Repeating", repertoire: "Repertoire", settings: "Settings",
  login: "Sign in", signup: "Create account",
};

export default function App() {
  const [route, setRoute] = useState(readRoute);
  const [appearance, setAppearance] = useState<Appearance>(loadAppearance);
  const [catalog, setCatalog] = useState<OpeningLine[]>([]);
  const [openingSort, setOpeningSort] = useState<OpeningSort>("easy");
  const [learningSide, setLearningSide] = useState<LearningSide>(() => {
    const saved = localStorage.getItem(learningSideKey);
    return saved === "white" || saved === "black" ? saved : "all";
  });
  const availableOpeningTypes = learningSide === "white" ? allOpeningTypes.filter((type) => type !== "defense") : allOpeningTypes;
  const [selectedOpeningTypes, setSelectedOpeningTypes] = useState<OpeningType[]>(availableOpeningTypes);
  const [repertoire, setRepertoire] = useState<Repertoire | null>(null);
  const [loadError, setLoadError] = useState("");
  const [loadVersion, setLoadVersion] = useState(0);
  const [session, setSession] = useState<(Session & { withoutHints?: boolean }) | null>(null);
  const [toast, setToast] = useState("");
  const [now, setNow] = useState(Date.now);
  const [account, setAccount] = useState<Account | null>(null);
  const [googleClientId, setGoogleClientId] = useState<string | null>(null);
  const progress = useProgress();

  // Who is signed in (the session lives in a cookie), then load their data.
  useEffect(() => {
    fetchAuthState().then(({ user, google_client_id }) => {
      setGoogleClientId(google_client_id);
      if (user) { rememberAccount(user); setAccount(user); setLoadVersion((version) => version + 1); }
    }).catch(() => { /* backend unreachable: the load banner explains it */ });
  }, []);

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
      const fresh = await practiceRequest<Repertoire>("repertoire");
      setRepertoire(fresh);
      setNow(Date.now());
      return fresh;
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
  // Swap the current history entry instead of adding one, so Back never returns to Sign in or Create account.
  const replaceRoute = useCallback((hash: string) => {
    if (window.location.hash === hash) setRoute(readRoute());
    else window.location.replace(hash);
  }, []);

  const showToast = useCallback((text: string) => {
    setToast(text);
    window.setTimeout(() => setToast((current) => (current === text ? "" : current)), 2800);
  }, []);

  const startLearning = useCallback<AppData["startLearning"]>(async (lineId, { restart = false, replayFrom, withoutHints } = {}) => {
    const line = lineById.get(lineId);
    if (!line) return;
    const side = line.family_side;          // every opening is learned from its family's side
    const saved = progress[lineId];
    const resumeAt = replayFrom ?? (!restart && saved?.side === side ? saved.ply : 0);
    const hideHints = withoutHints ?? Boolean(resumeAt && saved?.withoutHints);
    try {
      const started = await practiceRequest<Session>("learning", { line_id: lineId, side, ...(resumeAt ? { resume_at: resumeAt } : {}) });
      if (restart || (replayFrom !== undefined && started.move_index <= (side === "black" ? 1 : 0))) {
        clearProgress(lineId);
      } else if (replayFrom !== undefined) {
        saveProgress(lineId, { ply: started.move_index, total: started.total_plies, side, at: Date.now(), withoutHints: hideHints });
      }
      setSession({ ...started, withoutHints: hideHints });
      go("#/lesson");
    } catch (failure) {
      if (resumeAt && replayFrom === undefined) { clearProgress(lineId); showToast("The saved lesson could not be resumed, so it starts again."); }
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

  const signedIn = useCallback((user: Account) => {
    rememberAccount(user);
    setAccount(user);
    setSession(null);
    setLoadVersion((version) => version + 1);
    showToast(`Signed in as ${user.name}`);
    replaceRoute("#/home");
  }, [replaceRoute, showToast]);

  const leaveAccount = useCallback((message: string) => {
    rememberAccount(null);
    setAccount(null);
    setSession(null);
    setRepertoire(null);
    setLoadVersion((version) => version + 1);
    showToast(message);
    replaceRoute("#/login");
  }, [replaceRoute, showToast]);

  const signOut = useCallback(async () => {
    try { await logout(); } catch { /* the cookie is cleared on the next sign-in anyway */ }
    leaveAccount("Signed out");
  }, [leaveAccount]);

  const accountDeleted = useCallback(async () => leaveAccount("Your account was deleted"), [leaveAccount]);
  const accountChanged = useCallback((user: Account) => setAccount(user), []);

  // A signed-in player who lands on Sign in or Create account (for example with Back) goes to the dashboard.
  useEffect(() => {
    if (account && (route.view === "login" || route.view === "signup")) replaceRoute("#/home");
  }, [account, route.view, replaceRoute]);

  const dueCount = repertoire ? repertoire.lines.filter((line) => isDue(line, now)).length : 0;
  const data: AppData = {
    catalog, families, variants, lineById, repertoire, progress, now, go, showToast,
    openingSort, setOpeningSort, selectedOpeningTypes, setSelectedOpeningTypes,
    availableOpeningTypes, learningSide, setLearningSide,
    startLearning, startReview, refreshRepertoire, markLearned, dueCount, account, signOut, accountChanged, accountDeleted,
  };

  if (route.view === "login" || route.view === "signup") {
    return <AppearanceContext.Provider value={appearance}>
      <AuthPage mode={route.view} googleClientId={googleClientId} onSignedIn={signedIn} go={go} />
      <Toast text={toast} />
    </AppearanceContext.Provider>;
  }

  let page;
  switch (route.view) {
    case "learn": page = <LearnPage />; break;
    case "family": page = <FamilyPage name={route.arg ?? ""} />; break;
    case "lesson": page = session ? <LessonPage key={session.session_id} initial={session} withoutHints={session.withoutHints} onExit={(hash) => { setSession(null); go(hash); }} />
      : <LearnPage />; break;
    case "review": page = <ReviewPage />; break;
    case "repertoire": page = <RepertoirePage />; break;
    case "settings": page = <SettingsPage appearance={appearance} onChange={setAppearance}
      profile={<ProfileSettings key={route.arg ?? "settings"} startEditing={route.arg === "profile"} />} />; break;
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
