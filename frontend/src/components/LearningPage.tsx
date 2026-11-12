import { useEffect, useMemo, useRef, useState } from "react";
import { ArrowLeft, ArrowUpRight, Bookmark, Check, ChevronRight, RotateCcw } from "lucide-react";
import type { Square } from "chess.js";
import { openingLines, type OpeningLine } from "../data/openings";
import { advanceLearning, positionAt, suggestedMove } from "../lib/learning";
import { ChessBoard } from "./ChessBoard";
import "../learning.css";

export function LearningPage() {
  const [active, setActive] = useState<OpeningLine | null>(null);
  const [saved, setSaved] = useState<Set<string>>(() => new Set());
  const [learned, setLearned] = useState<Set<string>>(() => new Set());
  const heading = useRef<HTMLHeadingElement>(null);
  function showLibrary() {
    setActive(null);
    requestAnimationFrame(() => heading.current?.focus());
  }
  if (active) return <LearningSession key={active.id} opening={active} onExit={showLibrary} onComplete={() => {
    setLearned((previous) => new Set(previous).add(active.id));
  }} />;
  return <div className="page learning-page">
    <header className="learning-page-heading"><p className="eyebrow">LEARNING MODE</p>
      <h1 ref={heading} tabIndex={-1}>Build your repertoire.</h1>
      <p>Choose an opening. Follow the arrows. Understand every move.</p>
    </header>
    <section aria-labelledby="opening-family-title">
      <div className="opening-family-heading"><h2 id="opening-family-title">1. e4 <span>— King's Pawn Openings</span></h2>
        <span className="learning-side-badge">Playing as White</span></div>
      <div className="learning-opening-grid">
        {openingLines.map((opening) => {
          const preview = positionAt(opening.moves, opening.previewPly);
          const lastMove = preview.history({ verbose: true }).at(-1);
          const isSaved = saved.has(opening.id), isLearned = learned.has(opening.id);
          return <article className={`learning-opening-card ${isLearned ? "learning-opening-complete" : ""}`} key={opening.id}>
            <button type="button" className="learning-opening-main" onClick={() => setActive(opening)} aria-label={`Learn ${opening.name}`}>
              <div className="opening-board-preview"><ChessBoard fen={preview.fen()} lastMove={lastMove} />
                <span className="opening-board-side">WHITE</span></div>
              <div className="opening-card-copy"><h3>{opening.name}</h3><p>{opening.description}</p>
                <div className="opening-card-metadata"><span>{isLearned && <Check size={14} />} Learned <b>{isLearned ? 1 : 0}/1</b></span>
                  <span>{Math.ceil(opening.moves.length / 2)} guided moves</span></div>
                <span className="opening-start-link">{isLearned ? "Learn again" : "Start learning"}<ChevronRight size={17} /></span>
              </div>
            </button>
            <button type="button" className={`opening-bookmark ${isSaved ? "opening-bookmark-saved" : ""}`}
              aria-label={`${isSaved ? "Unsave" : "Save"} ${opening.name}`} aria-pressed={isSaved}
              onClick={() => setSaved((previous) => { const next = new Set(previous); if (next.has(opening.id)) next.delete(opening.id); else next.add(opening.id); return next; })}>
              <Bookmark size={19} fill={isSaved ? "currentColor" : "none"} />
            </button>
          </article>;
        })}
      </div>
    </section>
  </div>;
}

function LearningSession({ opening, onExit, onComplete }: { opening: OpeningLine; onExit: () => void; onComplete: () => void }) {
  const heading = useRef<HTMLHeadingElement>(null);
  useEffect(() => { heading.current?.focus(); }, []);
  const [ply, setPly] = useState(0);
  const [selected, setSelected] = useState<Square | null>(null);
  const [feedback, setFeedback] = useState("Follow the arrow: select the piece, then its destination.");
  const game = useMemo(() => positionAt(opening.moves, ply), [opening, ply]);
  const expected = useMemo(() => suggestedMove(opening.moves, ply), [opening, ply]);
  const finished = ply >= opening.moves.length;
  const total = Math.ceil(opening.moves.length / 2), completed = Math.ceil(ply / 2);
  const lastMove = game.history({ verbose: true }).at(-1);
  function attempt(from: Square, to: Square) {
    const next = advanceLearning(opening.moves, ply, from, to);
    setSelected(null);
    if (next === ply) {
      setFeedback(`Try again. Follow the arrow from ${expected?.from} to ${expected?.to}. Your position is unchanged.`);
      return;
    }
    setPly(next);
    if (next === opening.moves.length) { onComplete(); setFeedback("Line complete. You've played every move in this lesson."); }
    else setFeedback(`Correct — ${expected?.san}. Black's reply is on the board. Follow the next arrow.`);
  }
  function selectSquare(square: Square) {
    if (finished) return;
    if (square === selected) { setSelected(null); return; }
    if (selected) { attempt(selected, square); return; }
    if (game.get(square)?.color === "w") { setSelected(square); setFeedback(`Selected ${square}. Choose its destination.`); }
    else setFeedback("Choose a white piece, then follow the arrow.");
  }
  function restart() { setPly(0); setSelected(null); setFeedback("A fresh start. Follow the arrow to play your first move."); }
  return <div className="page learning-page learning-session">
    <button type="button" className="learning-back" onClick={onExit}><ArrowLeft size={17} /> All openings</button>
    <header className="learning-session-heading"><div><p className="eyebrow">GUIDED LEARNING · WHITE</p><h1 ref={heading} tabIndex={-1}>{opening.name}</h1></div>
      <span className="learning-side-badge">{completed} / {total} moves</span></header>
    <div className="learning-session-layout">
      <section className="lesson-board-panel" aria-label="Guided chessboard">
        <ChessBoard fen={game.fen()} arrow={expected} selected={selected} lastMove={lastMove} onSquareClick={finished ? undefined : selectSquare} />
        <p className="lesson-feedback" role="status">{feedback}</p>
      </section>
      <aside className="lesson-instructions">
        <div className="lesson-progress-heading"><span>Your progress</span><b>{Math.round(completed / total * 100)}%</b></div>
        <progress value={completed} max={total} aria-label="Lesson progress" />
        {finished ? <div className="lesson-completion"><span className="lesson-complete-icon"><Check size={28} /></span>
          <p className="eyebrow">LINE COMPLETE</p><h2>A new line in your repertoire.</h2><p>You've learned the moves. Revisit the line whenever you want a refresher.</p>
          <button type="button" className="primary-button full" onClick={onExit}>Back to openings<ChevronRight size={17} /></button>
          <p className="lesson-session-note">This demo keeps completion for this visit to Learning mode.</p>
        </div> : <>
          <div className="lesson-next-move"><span className="lesson-direction-icon"><ArrowUpRight size={24} /></span><div><span>YOUR NEXT MOVE</span>
            <h2>{Math.floor(ply / 2) + 1}. {expected?.san}</h2></div></div>
          <p className="lesson-explanation">{opening.explanations[Math.floor(ply / 2)]}</p>
          <div className="lesson-arrow-instruction"><b>{expected?.from} <span aria-hidden="true">→</span> {expected?.to}</b>
            <p>Follow the arrow on the board. Black's reply plays automatically.</p></div>
          <p className="lesson-input-help">Click or tap the piece, then the destination square. You can also Tab to a square and press Enter.</p>
        </>}
        <div className="lesson-moves"><h3>The line so far</h3><div>{ply === 0 ? <span className="lesson-moves-empty">Your first move starts the story.</span> :
          game.history().map((move, index) => <span className="lesson-move-chip" key={index}>{index % 2 === 0 && <small>{Math.floor(index / 2) + 1}.</small>} {move}</span>)}</div></div>
        <button type="button" className="secondary-button full lesson-restart" onClick={restart}><RotateCcw size={16} /> Restart line</button>
      </aside>
    </div>
  </div>;
}
