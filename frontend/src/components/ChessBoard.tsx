import { useEffect, useId, useRef, useState, type PointerEvent as ReactPointerEvent } from "react";
import { Chess, type Square } from "chess.js";

const symbols: Record<string, string> = { p: "♟", n: "♞", b: "♝", r: "♜", q: "♛", k: "♚" };
const names: Record<string, string> = { p: "pawn", n: "knight", b: "bishop", r: "rook", q: "queen", k: "king" };
const DRAG_THRESHOLD_PX = 5;
type MoveCoordinates = { from: Square; to: Square };
type Drag = { from: Square; startX: number; startY: number; x: number; y: number; moved: boolean };
type BoardProps = {
  fen: string;
  flipped?: boolean;
  disabled?: boolean;
  arrow?: MoveCoordinates | null;
  selected?: Square | null;
  lastMove?: MoveCoordinates | null;
  onSquareClick?: (square: Square) => void;
  /** Called when a piece is dragged from one square and dropped on another. */
  onPieceDrop?: (from: Square, to: Square) => void;
  /** Whether the piece on this square may be picked up. */
  canDrag?: (square: Square) => boolean;
};

export function ChessBoard({ fen, flipped = false, disabled = false, arrow, selected, lastMove, onSquareClick, onPieceDrop, canDrag }: BoardProps) {
  const markerId = useId().replace(/:/g, "");
  const board = useRef<HTMLDivElement>(null);
  const [drag, setDrag] = useState<Drag | null>(null);
  const dragRef = useRef<Drag | null>(null);
  const suppressClick = useRef(false);
  const game = new Chess(fen);
  const files = flipped ? "hgfedcba" : "abcdefgh";
  const ranks = flipped ? "12345678" : "87654321";
  const centre = (square: Square) => ({ x: files.indexOf(square[0]) * 100 + 50, y: ranks.indexOf(square[1]) * 100 + 50 });
  const start = arrow ? centre(arrow.from) : null;
  const end = arrow ? centre(arrow.to) : null;
  const angle = start && end ? Math.atan2(end.y - start.y, end.x - start.x) : 0;

  function squareAt(clientX: number, clientY: number): Square | null {
    const rect = board.current?.getBoundingClientRect();
    if (!rect) return null;
    const col = Math.floor((clientX - rect.left) / rect.width * 8);
    const row = Math.floor((clientY - rect.top) / rect.height * 8);
    if (col < 0 || col > 7 || row < 0 || row > 7) return null;
    return `${files[col]}${ranks[row]}` as Square;
  }

  function updateDrag(next: Drag | null) {
    dragRef.current = next;
    setDrag(next);
  }

  // Follow the pointer on the whole window, so a drag keeps working when it leaves the board.
  useEffect(() => {
    if (!drag) return;
    function move(event: PointerEvent) {
      const current = dragRef.current;
      if (!current) return;
      const moved = current.moved || Math.hypot(event.clientX - current.startX, event.clientY - current.startY) > DRAG_THRESHOLD_PX;
      updateDrag({ ...current, x: event.clientX, y: event.clientY, moved });
    }
    function finish(event: PointerEvent) {
      const current = dragRef.current;
      updateDrag(null);
      if (!current?.moved) return;            // a plain click: the square's click handler does the work
      suppressClick.current = true;           // ignore the click the browser fires after a drag
      window.setTimeout(() => { suppressClick.current = false; }, 0);
      const target = squareAt(event.clientX, event.clientY);
      if (target && target !== current.from) onPieceDrop?.(current.from, target);
    }
    function cancel() { updateDrag(null); }
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", finish);
    window.addEventListener("pointercancel", cancel);
    return () => {
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", finish);
      window.removeEventListener("pointercancel", cancel);
    };
  }, [drag !== null]); // eslint-disable-line react-hooks/exhaustive-deps

  function startDrag(event: ReactPointerEvent, square: Square) {
    if (disabled || !onPieceDrop || !canDrag?.(square) || event.button !== 0) return;
    if (event.pointerType === "mouse") event.preventDefault();   // no text selection while dragging
    updateDrag({ from: square, startX: event.clientX, startY: event.clientY, x: event.clientX, y: event.clientY, moved: false });
  }

  const dragging = drag?.moved ? drag : null;
  const boardRect = dragging ? board.current?.getBoundingClientRect() : undefined;
  const draggedPiece = dragging ? game.get(dragging.from) : undefined;
  const hoverSquare = dragging ? squareAt(dragging.x, dragging.y) : null;

  return <div ref={board} className={`learning-board ${dragging ? "learning-board-dragging" : ""}`} role={onSquareClick ? "group" : "img"}
    aria-label={`Chessboard, ${flipped ? "Black" : "White"} at the bottom`}>
    <div className="learning-board-squares">
      {Array.from({ length: 64 }, (_, index) => {
        const row = Math.floor(index / 8), col = index % 8;
        const square = `${files[col]}${ranks[row]}` as Square;
        const piece = game.get(square);
        const draggable = !disabled && !!onPieceDrop && !!piece && !!canDrag?.(square);
        const className = `learning-square ${(row + col) % 2 ? "learning-square-dark" : "learning-square-light"} ${selected === square ? "learning-square-selected" : ""} ${lastMove && (lastMove.from === square || lastMove.to === square) ? "learning-square-last" : ""} ${draggable ? "learning-square-draggable" : ""} ${hoverSquare === square && dragging?.from !== square ? "learning-square-drop" : ""}`;
        const content = <>
          {col === 0 && <small className="learning-rank" aria-hidden="true">{ranks[row]}</small>}
          {row === 7 && <small className="learning-file" aria-hidden="true">{files[col]}</small>}
          {piece && <span className={`learning-piece learning-piece-${piece.color} ${dragging?.from === square ? "learning-piece-lifted" : ""}`}
            aria-hidden="true">{symbols[piece.type]}</span>}
        </>;
        return onSquareClick ? <button type="button" key={square} className={className}
          aria-label={`${square}${piece ? `, ${piece.color === "w" ? "white" : "black"} ${names[piece.type]}` : ", empty"}`}
          aria-pressed={selected === square} aria-disabled={disabled}
          onPointerDown={(event) => startDrag(event, square)}
          onClick={() => {
            if (suppressClick.current) { suppressClick.current = false; return; }
            if (!disabled) onSquareClick(square);
          }}>{content}</button>
          : <div className={className} key={square} aria-hidden="true">{content}</div>;
      })}
    </div>
    {start && end && <svg className="learning-move-arrow" viewBox="0 0 800 800" aria-hidden="true">
      <defs><marker id={markerId} markerWidth="3.6" markerHeight="3.6" refX="2.8" refY="1.8" orient="auto">
        <path d="M0,0 L3.6,1.8 L0,3.6 Z" fill="currentColor" />
      </marker></defs>
      <line x1={start.x} y1={start.y} x2={end.x - Math.cos(angle) * 22} y2={end.y - Math.sin(angle) * 22}
        stroke="currentColor" strokeWidth="17" strokeLinecap="round" markerEnd={`url(#${markerId})`} />
    </svg>}
    {dragging && boardRect && draggedPiece && <span aria-hidden="true"
      className={`learning-piece learning-piece-${draggedPiece.color} learning-piece-ghost`}
      style={{ left: dragging.x - boardRect.left, top: dragging.y - boardRect.top }}>{symbols[draggedPiece.type]}</span>}
  </div>;
}
