import { useEffect, useMemo, useRef, useState } from "react";
import { ArrowLeft, ArrowUpRight, Check, ChevronRight, RotateCcw } from "lucide-react";
import type { Square } from "chess.js";
import { positionAt } from "../lib/learning";
import { practiceRequest, sideLabels, type OpeningLine, type Session } from "../lib/practiceApi";
import { addedMoves, groupVariations, variationLabel } from "../lib/variations";
import { ChessBoard } from "./ChessBoard";
import "../learning.css";

const promotions = { q: "Queen", r: "Rook", b: "Bishop", n: "Knight" };

export function PracticeSession({ initial, learning, onComplete, onExit, onRestart, currentLine, familyLines, onChooseVariation }: {
  initial: Session;
  learning: boolean;
  onComplete?: () => void;
  onExit: () => void;
  onRestart?: () => Promise<Session>;
  /** Learning only: the catalog entry being learned and the lines of its opening family. */
  currentLine?: OpeningLine;
  familyLines?: OpeningLine[];
  onChooseVariation?: (lineId: number) => Promise<void>;
}) {
  const heading = useRef<HTMLHeadingElement>(null);
  const [session, setSession] = useState(initial);
  const [selected, setSelected] = useState<Square | null>(null);
  const [promotion, setPromotion] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const game = useMemo(() => positionAt(session.played_moves, session.move_index), [session]);
  const finished = session.status === "complete";
  const turn = game.turn() === "w" ? "White" : "Black";
  const lastMove = game.history({ verbose: true }).at(-1);
  const hint = learning ? session.hint : null;
  const arrow = hint ? { from: hint.slice(0, 2) as Square, to: hint.slice(2, 4) as Square } : null;
  const variations = useMemo(() => currentLine && familyLines && onChooseVariation
    ? groupVariations(familyLines, currentLine) : null, [currentLine, familyLines, onChooseVariation]);

  useEffect(() => { heading.current?.focus(); }, []);

  async function update(request: () => Promise<Session>) {
    setBusy(true);
    setError("");
    try {
      const result = await request();
      setSession(result);
      setSelected(null);
      setPromotion("");
      if (result.status === "complete") onComplete?.();
    } catch (failure) {
      setError((failure as Error).message);
    } finally {
      setBusy(false);
    }
  }

  function submit(move: string) {
    void update(() => practiceRequest<Session>("move", {
      session_id: session.session_id, move_index: session.move_index, move_uci: move,
    }));
  }

  function attemptMove(from: Square, to: Square) {
    const move = from + to;
    if (game.get(from)?.type === "p" && to.endsWith(game.turn() === "w" ? "8" : "1")) {
      setPromotion(move);
    } else {
      submit(move);
    }
  }

  function selectSquare(square: Square) {
    const piece = game.get(square);
    if (piece?.color === game.turn()) {
      setSelected(selected === square ? null : square);
    } else if (selected) {
      attemptMove(selected, square);
    }
  }

  function dropPiece(from: Square, to: Square) {
    setSelected(null);
    attemptMove(from, to);
  }

  async function chooseVariation(lineId: number) {
    setBusy(true);
    setError("");
    try {
      await onChooseVariation?.(lineId);
    } catch (failure) {
      setError((failure as Error).message);
      setBusy(false);
    }
  }

  function variationButton(line: OpeningLine, extra: string | null) {
    const suggested = variations?.next?.line_id === line.line_id;
    return <li key={line.line_id}><button type="button" className="lesson-variation" disabled={busy}
      onClick={() => void chooseVariation(line.line_id)}>
      <span className="lesson-variation-copy"><b>{variationLabel(line)}</b>
        <small>{line.eco}{extra ? ` · ${extra}` : ` · ${line.moves_uci.split(" ").length} half-moves`}</small></span>
      {line.learned ? <span className="lesson-variation-tag lesson-variation-learned"><Check size={12} /> Learned</span>
        : suggested ? <span className="lesson-variation-tag">Suggested next</span> : null}
      <ChevronRight size={16} aria-hidden="true" />
    </button></li>;
  }

  const feedback = finished ? "Session complete."
    : session.correct === false ? "Try again. The board is unchanged."
    : `${turn} to move.${learning ? " Follow the arrow." : ""}`;
  return <div className="page learning-page learning-session">
    <button type="button" className="learning-back" disabled={busy} onClick={onExit}><ArrowLeft size={17} />
      {learning ? "All openings" : "Repeating & reviews"}</button>
    <header className="learning-session-heading">
      <div><p className="eyebrow">{learning ? "GUIDED LEARNING" : "REPEATING"} · {session.side && sideLabels[session.side]}</p>
        <h1 ref={heading} tabIndex={-1}>{session.name}</h1></div>
      <span className="learning-side-badge">{session.move_index} / {session.total_plies} half-moves</span>
    </header>
    <div className="learning-session-layout">
      <section className="lesson-board-panel" aria-label="Practice board" aria-busy={busy}>
        <ChessBoard fen={game.fen()} flipped={session.side === "black"} arrow={arrow} lastMove={lastMove} selected={selected}
          disabled={busy || !!promotion} onSquareClick={finished ? undefined : selectSquare}
          onPieceDrop={finished ? undefined : dropPiece}
          canDrag={(square) => !finished && game.get(square)?.color === game.turn()} />
        <p className="lesson-feedback" role="status">{feedback}</p>
        {error && <p role="alert">{error}</p>}
        {promotion && <div className="practice-controls" aria-label="Promotion piece">
          {Object.entries(promotions).map(([piece, label]) => <button key={piece} className="secondary-button"
            disabled={busy} onClick={() => submit(promotion + piece)}>{label}</button>)}
          <button className="secondary-button" disabled={busy} onClick={() => setPromotion("")}>Cancel</button>
        </div>}
      </section>
      <div className="lesson-side">
      <aside className="lesson-instructions">
        <div className="lesson-progress-heading"><span>Your progress</span><b>{Math.round(session.move_index / session.total_plies * 100)}%</b></div>
        <progress value={session.move_index} max={session.total_plies} aria-label="Session progress" />
        {finished ? <div className="lesson-completion"><span className="lesson-complete-icon"><Check size={28} /></span>
          <h2>{learning ? "Line saved to your repertoire." : "Review saved."}</h2>
          {session.fsrs_rating && <p>Review grade · {session.fsrs_rating}</p>}
          {variations?.next && <button className="primary-button full" disabled={busy}
            onClick={() => void chooseVariation(variations.next!.line_id)}>
            Learn next: {variationLabel(variations.next)}</button>}
          <button className={`${variations?.next ? "secondary-button" : "primary-button"} full`} onClick={onExit}>
            {learning ? "Back to openings" : "Done"}</button>
        </div> : arrow && <div className="lesson-next-move"><span className="lesson-direction-icon"><ArrowUpRight size={24} /></span>
          <div><span>YOUR NEXT MOVE</span><h2>{arrow.from} → {arrow.to}</h2></div>
        </div>}
        <div className="lesson-moves"><h3>The line so far</h3><div>
          {game.history().map((move, index) => <span className="lesson-move-chip" key={index}>
            {index % 2 === 0 && <small>{Math.floor(index / 2) + 1}.</small>} {move}</span>)}
        </div></div>
        {onRestart && <button type="button" className="secondary-button full lesson-restart" disabled={busy}
          onClick={() => void update(onRestart)}><RotateCcw size={16} /> Restart line</button>}
      </aside>
      {variations && currentLine && <section className="lesson-variations" aria-label={`Variations of ${currentLine.opening_family}`}>
        <p className="eyebrow">VARIATIONS</p>
        <h2>{currentLine.opening_family}</h2>
        <p className="lesson-variations-current">Now learning: <b>{variationLabel(currentLine)}</b> · {currentLine.eco}</p>
        {variations.continuations.length > 0 ? <>
          <h3>Continue this line <span>{variations.continuations.length}</span></h3>
          <ul className="lesson-variation-list">
            {variations.continuations.map((line) => variationButton(line, addedMoves(currentLine, line)))}
          </ul>
        </> : <p className="lesson-variations-empty">No longer line continues from here in this opening.</p>}
        {variations.others.length > 0 && <details className="lesson-variations-others" open={variations.continuations.length === 0}>
          <summary>Other variations <span>{variations.others.length}</span></summary>
          <ul className="lesson-variation-list">{variations.others.map((line) => variationButton(line, null))}</ul>
        </details>}
      </section>}
      </div>
    </div>
  </div>;
}
