import { useEffect, useMemo, useRef, useState, type PointerEvent as ReactPointerEvent } from "react";
import type { Square } from "chess.js";
import { ArrowLeft, ArrowUpRight, BookOpen, Check, ChevronLeft, ChevronRight, Lightbulb, Play, RotateCcw, Undo2 } from "lucide-react";
import { useApp } from "../lib/app";
import { closestLines, lineLabel, playerMoveCount, playerMovesIn } from "../lib/catalog";
import { positionAt } from "../lib/learning";
import { MAX_RESPONSE_MS, gradeExplanation } from "../lib/grading";
import { clearProgress, saveProgress } from "../lib/progress";
import { firstReviewWhen } from "../lib/memory";
import { isMobileApp } from "../lib/platform";
import { practiceRequest, type Grade, type RepertoireLine, type Session } from "../lib/practiceApi";
import { dragOffset, markArrivedBySwipe, swipeOutcome, arrivedBySwipe } from "../lib/swipe";
import { ChessBoard } from "./ChessBoard";
import { LineTitle, fmtDate, plural, sideName } from "./common";

const REVIEW_HINT_LIMIT = 4;
const promotions = { q: "Queen", r: "Rook", b: "Bishop", n: "Knight" } as const;
const gradeClass: Record<Grade, string> = { Again: "g1", Hard: "g2", Good: "g3", Easy: "g4" };

/** A running Learning or Repeating session against the backend. */
export function LessonPage({ initial, withoutHints = false, onExit }: {
  initial: Session; withoutHints?: boolean; onExit: (hash: string) => void;
}) {
  const { lineById, families, repertoire, progress, startLearning, startReview, refreshRepertoire, markLearned, showToast, dueCount } = useApp();
  const learning = initial.mode !== "repeating";
  const line = lineById.get(initial.line_id);
  const family = families.find((item) => item.name === line?.opening_family);
  const [session, setSession] = useState(initial);
  const [selected, setSelected] = useState<Square | null>(null);
  const [promotion, setPromotion] = useState("");
  const [busy, setBusy] = useState(false);
  const [pendingFinalMove, setPendingFinalMove] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<{ text: string; tone: "" | "ok" | "bad" }>(() =>
    learning && initial.move_index > 0 && progress[initial.line_id] ? { text: "Welcome back. You're continuing where you left off.", tone: "ok" } : { text: "", tone: "" });
  const [mistakes, setMistakes] = useState(0);
  const [hintMove, setHintMove] = useState<string | null>(null);
  const showRelearnChoice = !learning && mistakes > REVIEW_HINT_LIMIT;
  const [shake, setShake] = useState(0);
  const [reviewAfter, setReviewAfter] = useState<RepertoireLine | null>();
  const [learnedLine, setLearnedLine] = useState<RepertoireLine | null>(null);   // Learning: the saved first review
  const before = useRef(repertoire?.lines.find((item) => item.line_id === initial.line_id));

  const shown = session.move_index;
  const finished = session.status === "complete";
  const game = useMemo(() => {
    const position = positionAt(session.played_moves, shown);
    if (pendingFinalMove) position.move(pendingFinalMove);
    return position;
  }, [session.played_moves, shown, pendingFinalMove]);
  const yourTurn = !finished && !showRelearnChoice && !pendingFinalMove;
  // Move timing for grading (grading record, section 3.3): the clock starts when the player's position is ready.
  // A wrong attempt does not restart it, because only each move's first attempt is graded.
  const turnStartedAt = useRef(performance.now());
  useEffect(() => { if (yourTurn) turnStartedAt.current = performance.now(); }, [yourTurn, shown]);
  const guided = learning && !withoutHints;
  const hint = guided ? session.hint : hintMove;
  const legalMoves = useMemo(() => game.moves({ verbose: true }), [game]);
  const allowedMoves = hintMove ? legalMoves.filter((move) => move.lan === hintMove) : legalMoves;
  const arrow = yourTurn && hint ? { from: hint.slice(0, 2) as Square, to: hint.slice(2, 4) as Square, promotion: hint[4] } : null;
  const nextSan = useMemo(() => {
    if (!hint) return null;
    try { return positionAt(session.played_moves, session.move_index).move(hint).san; } catch { return hint; }
  }, [hint, session]);
  const lastMove = game.history({ verbose: true }).at(-1);
  const side = session.side ?? "white";
  const total = session.total_plies;
  // Progress counts the player's own moves: 4 for a 7-half-move line as White, 3 as Black.
  const movesDone = playerMovesIn(shown, side);
  const movesTotal = playerMovesIn(total, side);
  const firstPlayerPly = side === "black" ? 1 : 0;
  const lastPlayedPly = session.move_index - 1;
  const previousPlayerPly = side === "both" || lastPlayedPly % 2 === firstPlayerPly ? lastPlayedPly : lastPlayedPly - 1;

  const closest = useMemo(() => line && family ? closestLines(line, family.lines) : [], [line, family]);
  const nextLine = closest.find((item) => !item.line.learned && item.line.line_id !== initial.line_id)?.line;

  async function submit(move: string) {
    if (!yourTurn || busy || !allowedMoves.some((candidate) => candidate.lan === move)) return;
    const previous = session.move_index;
    // Confirm the final player move on the server while showing it on the board.
    const remaining = total - previous;
    if ((remaining === 1 || (side !== "both" && remaining === 2)) &&
        move === line?.moves_uci.split(" ")[previous]) {
      setPendingFinalMove(move);
    }
    setBusy(true);
    setSelected(null);
    setPromotion("");
    try {
      const responseTime = Math.min(MAX_RESPONSE_MS, Math.round(performance.now() - turnStartedAt.current));
      const next = await practiceRequest<Session>("move", {
        session_id: session.session_id, move_index: previous, move_uci: move, response_time_ms: responseTime,
      });
      setPendingFinalMove(null);
      setSession(next);
      if (next.correct) {
        setHintMove(null);
        setFeedback(mistakes && !learning ? { text: "Good, keep going.", tone: "ok" } : { text: "", tone: "" });
        if (learning && next.status === "play") {
          saveProgress(next.line_id, { ply: next.move_index, total: next.total_plies, side, at: Date.now(), withoutHints });
        }
        if (next.status === "complete") await complete(next);
      } else wrongMove(next);
    } catch (failure) {
      showToast((failure as Error).message);
    } finally {
      setPendingFinalMove(null);
      setBusy(false);
    }
  }

  function wrongMove(next: Session) {
    setShake((count) => count + 1);
    const count = mistakes + 1;
    setMistakes(count);
    if (guided) setFeedback({ text: "Not that move. Follow the arrow and try again.", tone: "bad" });
    else if (!learning && count > REVIEW_HINT_LIMIT) {
      setFeedback({ text: `${plural(count, "mistake")} in this line.`, tone: "bad" });
    } else {
      setHintMove((learning ? next.hint : next.expected_move) ?? null);
      setFeedback({ text: "Follow the arrow to continue.", tone: "bad" });
    }
  }

  async function complete(done: Session) {
    if (learning) {
      clearProgress(done.line_id);
      if (!withoutHints) {
        markLearned(done.line_id);
        showToast(`Added to your repertoire: ${line ? lineLabel(line) : done.name}`);
        const fresh = await refreshRepertoire();
        setLearnedLine(fresh?.lines.find((item) => item.line_id === done.line_id) ?? null);
      }
    } else {
      const fresh = await refreshRepertoire();
      setReviewAfter(fresh?.lines.find((item) => item.line_id === done.line_id) ?? null);
    }
  }

  // Repeating in the app: once a review is saved, swipe the board left for the next one.
  const [slideIn] = useState(() => !learning && arrivedBySwipe());
  const [swipeX, setSwipeX] = useState(0);
  const [swipeState, setSwipeState] = useState<"idle" | "dragging" | "leaving">("idle");
  const swipeStart = useRef<{ x: number; y: number; at: number; id: number } | null>(null);
  const canSwipeNext = finished && !learning && reviewAfter !== undefined && isMobileApp();

  function swipeDown(event: ReactPointerEvent<HTMLDivElement>) {
    if (!canSwipeNext || swipeState === "leaving" || event.pointerType === "mouse") return;
    swipeStart.current = { x: event.clientX, y: event.clientY, at: performance.now(), id: event.pointerId };
    setSwipeState("dragging");
  }
  function swipeMove(event: ReactPointerEvent<HTMLDivElement>) {
    const start = swipeStart.current;
    if (!start || start.id !== event.pointerId) return;
    setSwipeX(dragOffset(event.clientX - start.x, event.clientY - start.y));
  }
  async function swipeUp(event: ReactPointerEvent<HTMLDivElement>) {
    const start = swipeStart.current;
    if (!start || start.id !== event.pointerId) return;
    swipeStart.current = null;
    const width = event.currentTarget.getBoundingClientRect().width;
    const outcome = event.type === "pointercancel" ? "cancel"
      : swipeOutcome(event.clientX - start.x, event.clientY - start.y, performance.now() - start.at, width);
    if (outcome === "next" && dueCount > 0) {
      setSwipeState("leaving");
      setSwipeX(-width * 1.2);
      await new Promise((done) => setTimeout(done, 200));
      markArrivedBySwipe();
      await startReview();
    } else if (outcome === "next") {
      showToast("All caught up. Nothing else is due right now.");
    }
    setSwipeState("idle");
    setSwipeX(0);
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
    const candidates = allowedMoves.filter((move) => move.from === from && move.to === to);
    if (candidates.length > 1) setPromotion(from + to);
    else if (candidates.length === 1) void submit(candidates[0].lan);
  }

  async function replayLearning(replayFrom?: number, hideHints = withoutHints) {
    setBusy(true);
    try {
      await startLearning(session.line_id, { restart: replayFrom === undefined, replayFrom, withoutHints: hideHints });
    } finally {
      setBusy(false);
    }
  }
  function clickSquare(square: Square) {
    if (!yourTurn || busy) return;
    const piece = game.get(square);
    if (piece?.color === game.turn()) setSelected(selected === square || !allowedMoves.some((move) => move.from === square) ? null : square);
    else if (selected) attemptMove(selected, square);
  }

  const status = finished ? "Line complete." : pendingFinalMove ? "Finishing line…" : showRelearnChoice ? "Review ended."
    : `${game.turn() === "w" ? "White" : "Black"} to move. ${hint ? "Follow the arrow." : "Recall the move."}`;
  const title = line ? (lineLabel(line) === "Main line" ? line.opening_family : `${line.opening_family}: ${lineLabel(line)}`) : session.name;

  let panel;
  if (finished && learning) {
    panel = <div className="card learning-complete">
      <div className="learning-complete-header">
        <div className="done-icon" aria-hidden="true"><Check size={22} /></div>
        <div><h2>{withoutHints ? "Practice complete" : "Line learned"}</h2>
          <p className="muted">{withoutHints ? "Practice does not change your review schedule."
            : learnedLine && Date.parse(learnedLine.next_review_at) > Date.now()
              ? `First review ${firstReviewWhen(Date.parse(learnedLine.next_review_at), Date.now())}, once it has had a night to settle.`
              : "Ready to review."}</p></div>
      </div>
      <div className="done-actions">
        <button className="btn primary full" disabled={busy} onClick={() => void replayLearning(undefined, true)}><RotateCcw size={16} /> Practise without hints</button>
        {nextLine && <button className="btn ghost full" onClick={() => void startLearning(nextLine.line_id)}><Play size={16} /><span>Learn next: <LineTitle line={nextLine} /></span></button>}
        <button className="btn quiet full" onClick={() => onExit(`#/family/${encodeURIComponent(line?.opening_family ?? "")}`)}>Back to {line?.opening_family ?? "openings"}</button>
      </div></div>;
  } else if (finished) {
    const grade = session.fsrs_rating ?? "Again";
    const after = reviewAfter;
    const recallBefore = before.current?.recall;
    panel = <div className="card"><p className="eyebrow">REVIEW SAVED</p>
      <>
        <span className={`grade ${gradeClass[grade]}`}>{grade}</span>
        <p className="muted" style={{ margin: "12px 0 0", fontSize: 14 }}>{session.grading
          ? gradeExplanation(session.grading)
          : `This review was graded ${grade}.`}</p>
        <div className="facts">
          <div className="fact"><span>Recall before</span><b>{recallBefore == null ? "first test" : `${Math.round(recallBefore * 100)}%`}</b></div>
          <div className="fact"><span>Memory strength</span><b>{before.current?.stability_days != null ? `${before.current.stability_days.toFixed(1)} → ` : ""}{after?.stability_days != null ? `${after.stability_days.toFixed(1)} d` : "—"}</b></div>
          <div className="fact"><span>Next review</span><b>{after ? fmtDate(after.next_review_at) : "—"}</b></div>
          <div className="fact"><span>At</span><b>{after ? new Date(after.next_review_at).toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" }) : "—"}</b></div>
        </div>
      </>
      {after === undefined && <p className="muted small">Loading updated schedule...</p>}
      <div className="done-actions">
        <button className="btn primary full" onClick={() => void startReview()}><Play size={16} /> Next review</button>
        {grade === "Again" && <button className="btn ghost full" onClick={() => void startLearning(session.line_id, { restart: true })}><BookOpen size={16} /> Learn this line again</button>}
        <button className="btn quiet full" onClick={() => onExit("#/review")}>Done</button>
      </div></div>;
  } else if (showRelearnChoice) {
    panel = <div className="card choice" role="alertdialog" aria-labelledby="choice-h"><p className="eyebrow" style={{ color: "var(--hard)" }}>THIS LINE IS FADING</p>
      <h2 id="choice-h">Learn this line again?</h2>
      <p>You’ve used all four hints. Learn the line again with arrows to save this review as Again.</p>
      <button className="btn primary full" disabled={busy} onClick={() => void relearn()}><BookOpen size={16} /> Learn this line again</button>
    </div>;
  } else {
    panel = <div className="card">
      <div className="progress-head"><span>Your progress</span><b>{Math.round(movesDone / movesTotal * 100)}%</b></div>
      <div className="bar"><i style={{ width: `${movesDone / movesTotal * 100}%` }} /></div>
      {guided ? (yourTurn && nextSan ? <div className="next-move"><span className="icon"><ArrowUpRight size={24} /></span><div><span>YOUR NEXT MOVE</span><h2>{nextSan}</h2>
          <small className="muted">{hint!.slice(0, 2)} → {hint!.slice(2, 4)}</small></div></div>
        : null)
        : <div className="next-move"><span className="icon">{hintMove ? <Lightbulb size={22} /> : <RotateCcw size={22} />}</span><div>
          <span>{hintMove ? "HINT" : "YOUR NEXT MOVE"}</span><h2>{hintMove ? nextSan : "Recall the move"}</h2>
          <small className="muted">{mistakes ? `${plural(mistakes, "mistake")} so far` : "Mistakes: none yet"}</small></div></div>}
      <h3 style={{ marginBottom: 10 }}>The line so far</h3>
      <div className="moves">{game.history().map((move, index) => <span key={index} className="mv">{index % 2 === 0 && <small>{index / 2 + 1}.</small>}{move}</span>)}
        {shown === 0 && <span className="muted small">No moves yet.</span>}</div>
      {learning && <><hr className="divider" /><span className="muted small">Progress is saved automatically.</span></>}
    </div>;
  }

  return <>
    <button className="back" onClick={() => onExit(learning ? `#/family/${encodeURIComponent(line?.opening_family ?? "")}` : "#/review")}>
      <ArrowLeft size={16} /> {learning ? line?.opening_family ?? "Openings" : "Repeating"}</button>
    <div className="session-head"><div><p className="eyebrow">{guided ? "GUIDED LEARNING" : learning ? "LEARNING · RECALL PRACTICE" : "REPEATING"} · {sideName(side)}</p><h1>{title}</h1></div>
      <span className="badge">{movesDone} / {plural(movesTotal, "move")}</span></div>
    <div className="session">
      <div className="board-col">
        {learning && <div className="lesson-controls" role="group" aria-label="Learning controls">
          <button type="button" className="btn quiet" title="Replay previous move" aria-label="Replay previous move"
            disabled={busy || previousPlayerPly < firstPlayerPly} onClick={() => void replayLearning(previousPlayerPly)}><Undo2 size={18} /></button>
          <button type="button" className="btn quiet" title="Restart lesson" aria-label="Restart lesson"
            disabled={busy || (!finished && session.move_index <= firstPlayerPly)} onClick={() => void replayLearning()}><RotateCcw size={18} /></button>
        </div>}
        <div className={`board-frame${canSwipeNext ? " swipeable" : ""}${slideIn ? " slide-in" : ""}${swipeState === "dragging" ? " dragging" : ""}`}
          style={swipeX ? { transform: `translateX(${swipeX}px) rotate(${swipeX / 60}deg)`, opacity: swipeState === "leaving" ? 0 : 1 } : undefined}
          onPointerDown={swipeDown} onPointerMove={swipeMove} onPointerUp={(event) => void swipeUp(event)} onPointerCancel={(event) => void swipeUp(event)}>
        <ChessBoard fen={game.fen()} flipped={side === "black"} arrow={arrow} lastMove={lastMove} selected={selected} shake={shake}
          disabled={busy || !yourTurn || !!promotion} onSquareClick={clickSquare}
          onPieceDrop={finished ? undefined : (from, to) => { setSelected(null); if (yourTurn && !busy) attemptMove(from, to); }}
          canDrag={(square) => yourTurn && !busy && allowedMoves.some((move) => move.from === square)} /></div>
        <p className={`feedback ${feedback.tone}`} role="status">{feedback.text || status}</p>
        {canSwipeNext && <p className="swipe-hint" aria-hidden="true">{dueCount > 0
          ? <><ChevronLeft size={16} /> Swipe the board for the next review · {dueCount} due</>
          : "All caught up. Nothing else is due right now."}</p>}
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
  let detail = plural(playerMoveCount(line), "move");
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
