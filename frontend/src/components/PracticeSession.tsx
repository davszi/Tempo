import { useEffect, useMemo, useRef, useState } from "react";
import { ArrowLeft, ArrowUpRight, Check, RotateCcw } from "lucide-react";
import type { Square } from "chess.js";
import { positionAt } from "../lib/learning";
import { practiceRequest, sideLabels, type Session } from "../lib/practiceApi";
import { ChessBoard } from "./ChessBoard";
import "../learning.css";

const promotions = { q: "Queen", r: "Rook", b: "Bishop", n: "Knight" };

export function PracticeSession({ initial, learning, onComplete, onExit, onRestart }: {
  initial: Session;
  learning: boolean;
  onComplete?: () => void;
  onExit: () => void;
  onRestart?: () => Promise<Session>;
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

  function selectSquare(square: Square) {
    const piece = game.get(square);
    if (piece?.color === game.turn()) {
      setSelected(selected === square ? null : square);
    } else if (selected) {
      const move = selected + square;
      if (game.get(selected)?.type === "p" && square.endsWith(game.turn() === "w" ? "8" : "1")) {
        setPromotion(move);
      } else {
        submit(move);
      }
    }
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
          disabled={busy || !!promotion} onSquareClick={finished ? undefined : selectSquare} />
        <p className="lesson-feedback" role="status">{feedback}</p>
        {error && <p role="alert">{error}</p>}
        {promotion && <div className="practice-controls" aria-label="Promotion piece">
          {Object.entries(promotions).map(([piece, label]) => <button key={piece} className="secondary-button"
            disabled={busy} onClick={() => submit(promotion + piece)}>{label}</button>)}
          <button className="secondary-button" disabled={busy} onClick={() => setPromotion("")}>Cancel</button>
        </div>}
      </section>
      <aside className="lesson-instructions">
        <div className="lesson-progress-heading"><span>Your progress</span><b>{Math.round(session.move_index / session.total_plies * 100)}%</b></div>
        <progress value={session.move_index} max={session.total_plies} aria-label="Session progress" />
        {finished ? <div className="lesson-completion"><span className="lesson-complete-icon"><Check size={28} /></span>
          <h2>{learning ? "Line saved to your repertoire." : "Review saved."}</h2>
          {session.fsrs_rating && <p>Review grade · {session.fsrs_rating}</p>}
          <button className="primary-button full" onClick={onExit}>{learning ? "Back to openings" : "Done"}</button>
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
    </div>
  </div>;
}
