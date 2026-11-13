import { useEffect, useState } from "react";
import { Bookmark, Check, ChevronRight } from "lucide-react";
import { positionAt } from "../lib/learning";
import { practiceRequest, sideLabels, sides, type OpeningLine, type Session, type Side } from "../lib/practiceApi";
import { ChessBoard } from "./ChessBoard";
import { PracticeSession } from "./PracticeSession";

export function LearningPage() {
  const [catalog, setCatalog] = useState<OpeningLine[]>([]);
  const [saved, setSaved] = useState<Set<number>>(() => new Set());
  const [query, setQuery] = useState("");
  const [side, setSide] = useState<Side>("white");
  const [limit, setLimit] = useState(12);
  const [session, setSession] = useState<Session>();
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [catalogVersion, setCatalogVersion] = useState(0);

  useEffect(() => {
    const request = new AbortController();
    practiceRequest<OpeningLine[]>("catalog", {}, request.signal)
      .then((lines) => { if (!request.signal.aborted) setCatalog(lines); })
      .catch((failure: Error) => { if (!request.signal.aborted) setError(failure.message); })
      .finally(() => { if (!request.signal.aborted) setLoading(false); });
    return () => request.abort();
  }, [catalogVersion]);

  const term = query.trim().toLowerCase();
  const matches = catalog.filter((line) =>
    (side === "white" || line.moves_uci.includes(" ")) &&
    [line.name, line.opening_family, line.eco].some((value) => value.toLowerCase().includes(term)));

  function open(lineId: number) {
    return practiceRequest<Session>("learning", { line_id: lineId, side });
  }

  async function start(lineId: number) {
    setBusy(true);
    setError("");
    try {
      setSession(await open(lineId));
    } catch (failure) {
      setError((failure as Error).message);
    } finally {
      setBusy(false);
    }
  }

  if (session) {
    const currentLine = catalog.find((line) => line.line_id === session.line_id);
    const familyLines = currentLine ? catalog.filter((line) => line.opening_family === currentLine.opening_family &&
      (side === "white" || line.moves_uci.includes(" "))) : undefined;
    return <PracticeSession key={session.session_id} initial={session} learning
      currentLine={currentLine} familyLines={familyLines}
      onChooseVariation={async (lineId) => setSession(await open(lineId))}
      onRestart={() => open(session.line_id)}
      onComplete={() => setCatalog((previous) => previous.map((line) =>
        line.line_id === session.line_id ? { ...line, learned: true } : line))}
      onExit={() => setSession(undefined)} />;
  }

  return <div className="page learning-page">
    <header className="learning-page-heading"><p className="eyebrow">LEARNING MODE</p>
      <h1>Build your repertoire.</h1><p>Choose an opening line and follow the arrows on the board.</p>
    </header>
    <div className="practice-controls">
      <label>Search openings <input type="search" value={query} onChange={(event) => { setQuery(event.target.value); setLimit(12); }} /></label>
      <label>Play as <select value={side} disabled={busy} onChange={(event) => { setSide(event.target.value as Side); setLimit(12); }}>
        {sides.map((option) => <option key={option} value={option}>{sideLabels[option]}</option>)}
      </select></label>
    </div>
    {error && <p role="alert">{error}</p>}
    {error && catalog.length === 0 && <button className="secondary-button" onClick={() => {
      setError(""); setLoading(true); setCatalogVersion((version) => version + 1);
    }}>Reload openings</button>}
    {loading && <p role="status">Loading openings…</p>}
    {!loading && !error && <p>{matches.length} matching lines</p>}
    <div className="learning-opening-grid">
      {matches.slice(0, limit).map((line) => {
        const moves = line.moves_uci.split(" ");
        const preview = positionAt(moves, 4);
        const isSaved = saved.has(line.line_id);
        return <article className={`learning-opening-card ${line.learned ? "learning-opening-complete" : ""}`} key={line.line_id}>
          <button type="button" className="learning-opening-main" disabled={busy} onClick={() => void start(line.line_id)}>
            <div className="opening-board-preview"><ChessBoard fen={preview.fen()} lastMove={preview.history({ verbose: true }).at(-1)}
              flipped={side === "black"} /></div>
            <div className="opening-card-copy"><h3>{line.name}</h3><p>{line.opening_family} · {line.eco}</p>
              <div className="opening-card-metadata"><span>{line.learned && <Check size={14} />} {line.learned ? "Learned" : "New line"}</span></div>
              <span className="opening-start-link">{line.learned ? "Learn again" : "Start learning"}<ChevronRight size={17} /></span>
            </div>
          </button>
          <button type="button" className={`opening-bookmark ${isSaved ? "opening-bookmark-saved" : ""}`}
            aria-label={`${isSaved ? "Unsave" : "Save"} ${line.name}`} aria-pressed={isSaved}
            onClick={() => setSaved((previous) => {
              const next = new Set(previous);
              if (isSaved) next.delete(line.line_id);
              else next.add(line.line_id);
              return next;
            })}><Bookmark size={19} fill={isSaved ? "currentColor" : "none"} /></button>
        </article>;
      })}
    </div>
    {matches.length > limit && <button className="secondary-button" onClick={() => setLimit(limit + 12)}>Show more lines</button>}
  </div>;
}
