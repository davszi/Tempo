import { useEffect, useMemo, useRef, useState } from "react";
import type { Square } from "chess.js";
import { ArrowLeft, ArrowUpRight, BookOpen, Check, ChevronRight, Lightbulb, Play, RotateCcw, Sparkles } from "lucide-react";
import { useApp } from "../lib/app";
import { closestLines, lineLabel } from "../lib/catalog";
import { positionAt } from "../lib/learning";
import { clearProgress, saveProgress } from "../lib/progress";
import { practiceRequest, type Grade, type RepertoireLine, type Session } from "../lib/practiceApi";
import { ChessBoard } from "./ChessBoard";
import { LineTitle, fmtDate, plural, sideName } from "./common";

const OPPONENT_DELAY_MS = 450;
const promotions = { q: "Queen", r: "Rook", b: "Bishop", n: "Knight" } as const;
const gradeClass: Record<Grade, string> = { Again: "g1", Hard: "g2", Good: "g3", Easy: "g4" };
const gradeReason: Record<Grade, string> = {
  Again: "A mistake in this line, so it counts as Again, even when fixed on retry.",
  Hard: "No mistakes, but slow: over 1.8 s of thinking per move.",
  Good: "No mistakes, with 0.5 to 1.8 s of thinking per move.",
  Easy: "No mistakes and fast: under 0.5 s of thinking per move.",
};

/** A running Learning or Repeating session against the backend. */
export function LessonPage({ initial, onExit }: { initial: Session; onExit: (hash: string) => void }) {
  const { lineById, families, repertoire, progress, startLearning, startReview, refreshRepertoire, markLearned, showToast } = useApp();
  const learning = initial.mode !== "repeating";
  const line = lineById.get(initial.line_id);
  const family = families.find((item) => item.name === line?.opening_family);
  const [session, setSession] = useState(initial);
  const [shown, setShown] = useState(initial.move_index);       // ply on the board; lags while the opponent "replies"
  const [selected, setSelected] = useState<Square | null>(null);
  const [promotion, setPromotion] = useState("");
  const [busy, setBusy] = useState(false);
  const [feedback, setFeedback] = useState<{ text: string; tone: "" | "ok" | "bad" }>(() =>
    learning && initial.move_index > 0 && progress[initial.line_id] ? { text: "Welcome back. You're continuing where you left off.", tone: "ok" } : { text: "", tone: "" });
  const [mistakes, setMistakes] = useState(0);
  const [hintMove, setHintMove] = useState<string | null>(null);   // Repeating: the move shown once after a mistake
  const [choice, setChoice] = useState<"closed" | "open" | "used">("closed");
  const [shake, setShake] = useState(0);
  const [result, setResult] = useState<{ grade: Grade; before: RepertoireLine | undefined; after?: RepertoireLine } | null>(null);
  const before = useRef(repertoire?.lines.find((item) => item.line_id === initial.line_id));
  const timer = useRef<number | undefined>(undefined);
  useEffect(() => () => window.clearTimeout(timer.current), []);

  const finished = session.status === "complete";
  const game = useMemo(() => positionAt(session.played_moves, shown), [session, shown]);
  const animating = shown < session.move_index;
  const yourTurn = !finished && !animating && choice !== "open";
  const hint = learning ? session.hint : hintMove;
  const arrow = yourTurn && hint ? { from: hint.slice(0, 2) as Square, to: hint.slice(2, 4) as Square } : null;
  const nextSan = useMemo(() => {
    if (!hint) return null;
    try { return positionAt(session.played_moves, session.move_index).move(hint).san; } catch { return hint; }
  }, [hint, session]);
  const lastMove = game.history({ verbose: true }).at(-1);
  const side = session.side ?? "white";
  const total = session.total_plies;

  const closest = useMemo(() => line && family ? closestLines(line, family.lines) : [], [line, family]);
  const nextLine = closest.find((item) => !item.line.learned && item.line.line_id !== initial.line_id)?.line;

  async function submit(move: string) {
    const previous = session.move_index;
    setBusy(true);
    setSelected(null);
    setPromotion("");
    try {
      const next = await practiceRequest<Session>("move", { session_id: session.session_id, move_index: previous, move_uci: move });
      setSession(next);
      if (next.correct) {
        setHintMove(null);
        setFeedback(mistakes && !learning ? { text: "Good, keep going.", tone: "ok" } : { text: "", tone: "" });
        // Learning: show your move first, then the opponent's reply. Repeating stays instant, because reply time is graded.
        if (learning && next.move_index > previous + 1) {
          setShown(previous + 1);
          timer.current = window.setTimeout(() => setShown(next.move_index), OPPONENT_DELAY_MS);
        } else setShown(next.move_index);
        if (learning && next.status === "play") saveProgress(next.line_id, { ply: next.move_index, total: next.total_plies, side, at: Date.now() });
        if (next.status === "complete") await complete(next);
      } else wrongMove(next);
    } catch (failure) {
      showToast((failure as Error).message);
    } finally {
      setBusy(false);
    }
  }

  function wrongMove(next: Session) {
    setShake((count) => count + 1);
    const count = mistakes + 1;
    setMistakes(count);
    if (learning) setFeedback({ text: "Not that move. Follow the arrow and try again.", tone: "bad" });
    else if (count === 1) {
      setHintMove(next.expected_move ?? null);
      setFeedback({ text: "Not quite. Here's the move once. Play it to continue.", tone: "bad" });
    } else if (choice === "closed") {
      setHintMove(null);
      setChoice("open");
      setFeedback({ text: "Second mistake in this line.", tone: "bad" });
    } else setFeedback({ text: "Try again. The board is unchanged.", tone: "bad" });
  }

  async function complete(done: Session) {
    if (learning) {
      clearProgress(done.line_id);
      markLearned(done.line_id);
      showToast(`Added to your repertoire: ${line ? lineLabel(line) : done.name}`);
      await refreshRepertoire();
    } else {
      const fresh = await practiceRequest<{ lines: RepertoireLine[] }>("repertoire");
      void refreshRepertoire();
      setResult({ grade: done.fsrs_rating ?? "Again", before: before.current, after: fresh.lines.find((item) => item.line_id === done.line_id) });
    }
  }

  async function relearn() {
    setBusy(true);
    try {
      await practiceRequest("review/abandon", { session_id: session.session_id });
      showToast("Review saved as Again. Let's learn it again.");
      await startLearning(session.line_id, { restart: true });
    } catch (failure) {
      showToast((failure as Error).message);
      setBusy(false);
    }
  }

  function attemptMove(from: Square, to: Square) {
    const move = from + to;
    if (game.get(from)?.type === "p" && to.endsWith(game.turn() === "w" ? "8" : "1")) setPromotion(move);
    else void submit(move);
  }
  function clickSquare(square: Square) {
    if (!yourTurn || busy) return;
    const piece = game.get(square);
    if (piece?.color === game.turn()) setSelected(selected === square ? null : square);
    else if (selected) attemptMove(selected, square);
  }

  const status = finished ? "Line complete." : choice === "open" ? "Choose how to continue."
    : animating ? "Opponent is replying…"
    : learning ? `${game.turn() === "w" ? "White" : "Black"} to move. Follow the arrow, drag the piece or click it and then its square.`
    : `${game.turn() === "w" ? "White" : "Black"} to move. Recall the move: no hints.`;
  const title = line ? (lineLabel(line) === "Main line" ? line.opening_family : `${line.opening_family}: ${lineLabel(line)}`) : session.name;

  let panel;
  if (finished && learning) {
    panel = <div className="card"><div className="done-icon"><Check size={26} /></div><h2>Learned and added to your repertoire.</h2>
      <p className="muted" style={{ margin: "8px 0 0" }}>{title} as {sideName(side)}. Its first recall test is ready now, then TEMPO spaces the reviews out.</p>
      <div className="done-actions">
        <button className="btn primary full" onClick={() => void startReview(session.line_id)}><RotateCcw size={16} /> Test it now without hints</button>
        {nextLine && <button className="btn ghost full" onClick={() => void startLearning(nextLine.line_id)}><Play size={16} /> Learn next: <LineTitle line={nextLine} /></button>}
        <button className="btn quiet full" onClick={() => onExit(`#/family/${encodeURIComponent(line?.opening_family ?? "")}`)}>Back to {line?.opening_family ?? "openings"}</button>
      </div></div>;
  } else if (finished) {
    const grade = result?.grade;
    const after = result?.after;
    const recallBefore = result?.before?.recall;
    panel = <div className="card"><p className="eyebrow">REVIEW SAVED</p>
      {grade ? <>
        <span className={`grade ${gradeClass[grade]}`}>{grade}</span>
        <p className="muted" style={{ margin: "12px 0 0", fontSize: 14 }}>{mistakes ? `${plural(mistakes, "mistake")} in this line. Any mistake means Again, even when fixed on retry.` : gradeReason[grade]}</p>
        <div className="facts">
          <div className="fact"><span>Recall before</span><b>{recallBefore == null ? "first test" : `${Math.round(recallBefore * 100)}%`}</b></div>
          <div className="fact"><span>Memory strength</span><b>{result?.before?.stability_days != null ? `${result.before.stability_days.toFixed(1)} → ` : ""}{after?.stability_days != null ? `${after.stability_days.toFixed(1)} d` : "—"}</b></div>
          <div className="fact"><span>Next review</span><b>{after ? fmtDate(after.next_review_at) : "—"}</b></div>
          <div className="fact"><span>At</span><b>{after ? new Date(after.next_review_at).toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" }) : "—"}</b></div>
        </div>
      </> : <p className="muted">Saving…</p>}
      <div className="done-actions">
        <button className="btn primary full" onClick={() => void startReview()}><Play size={16} /> Next review</button>
        {grade === "Again" && <button className="btn ghost full" onClick={() => void startLearning(session.line_id, { restart: true })}><BookOpen size={16} /> Learn this line again</button>}
        <button className="btn quiet full" onClick={() => onExit("#/review")}>Done</button>
      </div></div>;
  } else if (choice === "open") {
    panel = <div className="card choice" role="alertdialog" aria-labelledby="choice-h"><p className="eyebrow" style={{ color: "var(--hard)" }}>THIS LINE IS FADING</p>
      <h2 id="choice-h">You missed a move twice.</h2>
      <p>You can go back and learn {line ? lineLabel(line) : "this line"} again with the arrows, or keep going on your own. Either way this review counts as Again, so it comes back soon.</p>
      <button className="btn primary full" disabled={busy} onClick={() => void relearn()}><BookOpen size={16} /> Learn this line again</button>
      <button className="btn ghost full" disabled={busy} onClick={() => { setChoice("used"); setFeedback({ text: "Keep going. No more hints in this line.", tone: "" }); }}><Play size={16} /> Continue this line</button></div>;
  } else {
    panel = <div className="card">
      <div className="progress-head"><span>Your progress</span><b>{Math.round(shown / total * 100)}%</b></div>
      <div className="bar"><i style={{ width: `${shown / total * 100}%` }} /></div>
      {learning ? (yourTurn && nextSan ? <div className="next-move"><span className="icon"><ArrowUpRight size={24} /></span><div><span>YOUR NEXT MOVE</span><h2>{nextSan}</h2>
          <small className="muted">{hint!.slice(0, 2)} → {hint!.slice(2, 4)}</small></div></div>
        : <div className="next-move"><span className="icon"><Sparkles size={22} /></span><div><span>OPPONENT</span><h2>Thinking…</h2></div></div>)
        : <div className="next-move"><span className="icon">{hintMove ? <Lightbulb size={22} /> : <RotateCcw size={22} />}</span><div>
          <span>{hintMove ? "ONE-TIME HINT" : "NO HINTS"}</span><h2>{hintMove ? nextSan : "Recall the move"}</h2>
          <small className="muted">{mistakes ? `${plural(mistakes, "mistake")} so far` : "Mistakes: none yet"}</small></div></div>}
      <h3 style={{ marginBottom: 10 }}>The line so far</h3>
      <div className="moves">{game.history().map((move, index) => <span key={index} className="mv">{index % 2 === 0 && <small>{index / 2 + 1}.</small>}{move}</span>)}
        {shown === 0 && <span className="muted small">No moves yet.</span>}</div>
      {learning && <><hr className="divider" /><div className="row">
        <button className="btn sm ghost" disabled={busy} onClick={() => void startLearning(session.line_id, { restart: true })}><RotateCcw size={15} /> Restart line</button>
        <span className="muted small">Progress is saved automatically.</span></div></>}
    </div>;
  }

  return <>
    <button className="back" onClick={() => onExit(learning ? `#/family/${encodeURIComponent(line?.opening_family ?? "")}` : "#/review")}>
      <ArrowLeft size={16} /> {learning ? line?.opening_family ?? "Openings" : "Repeating"}</button>
    <div className="session-head"><div><p className="eyebrow">{learning ? "GUIDED LEARNING" : "REPEATING · NO HINTS"} · {sideName(side)}</p><h1>{title}</h1></div>
      <span className="badge">{shown} / {total} half-moves</span></div>
    <div className="session">
      <div className="board-col"><div className="board-frame">
        <ChessBoard fen={game.fen()} flipped={side === "black"} arrow={arrow} lastMove={lastMove} selected={selected} shake={shake}
          disabled={busy || !yourTurn || !!promotion} onSquareClick={finished ? undefined : clickSquare}
          onPieceDrop={finished ? undefined : (from, to) => { setSelected(null); if (yourTurn && !busy) attemptMove(from, to); }}
          canDrag={(square) => yourTurn && !busy && game.get(square)?.color === game.turn()} /></div>
        <p className={`feedback ${feedback.tone}`} role="status">{feedback.text || status}</p>
        {promotion && <div className="row" aria-label="Promotion piece">{Object.entries(promotions).map(([piece, label]) =>
          <button key={piece} className="btn sm ghost" disabled={busy} onClick={() => void submit(promotion + piece)}>{label}</button>)}
          <button className="btn sm quiet" onClick={() => setPromotion("")}>Cancel</button></div>}
      </div>
      <div className="stack">{panel}
        {learning && line && family && <section className="card" aria-label={`Variations of ${family.name}`}>
          <p className="eyebrow">VARIATIONS</p><h2>{family.name}</h2>
          <p className="muted small" style={{ margin: "6px 0 14px" }}>Now learning: <b style={{ color: "var(--accent)" }}><LineTitle line={line} /></b> · {line.eco}</p>
          {closest.length ? <>
            <div className="section-title" style={{ marginTop: 0 }}>Closest to this line <span className="chip plain">{Math.min(8, closest.length)}</span></div>
            <ul className="list scroll">{closest.slice(0, 8).map(({ line: other, shared }) => <li key={other.line_id}>
              <VariationItem lineId={other.line_id} shared={shared} suggested={other === nextLine} /></li>)}</ul>
            {closest.length > 8 && <details className="more"><summary>Other variations <span className="chip plain">{closest.length - 8}</span></summary>
              <ul className="list scroll" style={{ marginTop: 10 }}>{closest.slice(8).map(({ line: other }) => <li key={other.line_id}>
                <VariationItem lineId={other.line_id} suggested={false} /></li>)}</ul></details>}
          </> : <p className="muted small" style={{ margin: 0 }}>This is the only line of this opening.</p>}
        </section>}
      </div>
    </div>
  </>;
}

function VariationItem({ lineId, shared, suggested }: { lineId: number; shared?: number; suggested: boolean }) {
  const { lineById, progress, startLearning } = useApp();
  const line = lineById.get(lineId)!;
  const moves = line.moves_uci.split(" ");
  let detail = `${moves.length} half-moves`;
  if (shared != null && shared < moves.length) {
    const san = positionAt(moves, moves.length).history();
    const ply = shared;
    detail = `branches at ${Math.floor(ply / 2) + 1}${ply % 2 ? "…" : "."} ${san[ply]}`;
  }
  return <button className="item" onClick={() => void startLearning(lineId)}>
    <span className="grow"><b><LineTitle line={line} /></b><small>{line.eco} · {detail}</small></span>
    {line.learned ? <span className="chip"><Check size={12} /> Learned</span> : progress[lineId] ? <span className="chip warn">In progress</span>
      : suggested ? <span className="chip warn">Suggested next</span> : null}
    <ChevronRight size={16} /></button>;
}
