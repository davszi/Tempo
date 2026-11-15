import { useEffect, useId, useRef, useState, type PointerEvent as ReactPointerEvent } from "react";
import { createPortal } from "react-dom";
import { Chess, type Square } from "chess.js";
import { pieceImage, useAppearance } from "../lib/appearance";

const names: Record<string, string> = { p: "pawn", n: "knight", b: "bishop", r: "rook", q: "queen", k: "king" };
const DRAG_THRESHOLD_PX = 5;
type MoveCoordinates = { from: Square; to: Square };
type Drag = { from: Square; startX: number; startY: number; x: number; y: number; moved: boolean; size: number };
type BoardProps = {
  fen: string;
  flipped?: boolean;
  disabled?: boolean;
  /** Small preview: no coordinates, not interactive. */
  mini?: boolean;
  arrow?: MoveCoordinates | null;
  selected?: Square | null;
  lastMove?: MoveCoordinates | null;
  shake?: number;
  onSquareClick?: (square: Square) => void;
  /** Called when a piece is dragged from one square and dropped on another. */
  onPieceDrop?: (from: Square, to: Square) => void;
  /** Whether the piece on this square may be picked up. */
  canDrag?: (square: Square) => boolean;
};

export function ChessBoard({ fen, flipped = false, disabled = false, mini = false, arrow, selected, lastMove, shake = 0,
  onSquareClick, onPieceDrop, canDrag }: BoardProps) {
  const { theme, pieces } = useAppearance();
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
  const image = (color: string, type: string) => pieceImage(pieces, color + type.toUpperCase(), theme);

  // Replay the shake animation when the parent reports a wrong move.
  useEffect(() => {
    if (!shake || !board.current) return;
    board.current.classList.remove("shake");
    void board.current.offsetWidth;
    board.current.classList.add("shake");
  }, [shake]);

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

  function startDrag(event: ReactPointerEvent<HTMLElement>, square: Square) {
    if (disabled || !onPieceDrop || !canDrag?.(square) || event.button !== 0) return;
    if (event.pointerType === "mouse") event.preventDefault();   // no text selection while dragging
    const size = event.currentTarget.getBoundingClientRect().width;
    updateDrag({ from: square, startX: event.clientX, startY: event.clientY, x: event.clientX, y: event.clientY, moved: false, size });
  }

  const dragging = drag?.moved ? drag : null;
  const draggedPiece = dragging ? game.get(dragging.from) : undefined;
  const hoverSquare = dragging ? squareAt(dragging.x, dragging.y) : null;
  const interactive = !!onSquareClick;

  return <div ref={board} className={`board ${interactive ? "interactive" : ""} ${mini ? "mini" : ""}`}
    role={interactive ? "group" : "img"} aria-label={`Chessboard, ${flipped ? "Black" : "White"} at the bottom`}>
    <div className="squares">
      {Array.from({ length: 64 }, (_, index) => {
        const row = Math.floor(index / 8), col = index % 8;
        const square = `${files[col]}${ranks[row]}` as Square;
        const piece = game.get(square);
        const mine = !disabled && !!onPieceDrop && !!piece && !!canDrag?.(square);
        const className = ["sq", (row + col) % 2 ? "d" : "l",
          lastMove && (lastMove.from === square || lastMove.to === square) ? "last" : "",
          selected === square ? "sel" : "", mine ? "mine" : "",
          hoverSquare === square && dragging?.from !== square ? "drop" : ""].join(" ");
        const content = <>
          {!mini && col === 0 && <small className="coord r" aria-hidden="true">{ranks[row]}</small>}
          {!mini && row === 7 && <small className="coord f" aria-hidden="true">{files[col]}</small>}
          {piece && <span className={`pc ${dragging?.from === square ? "lifted" : ""}`} aria-hidden="true">
            <img src={image(piece.color, piece.type)} alt="" draggable={false} /></span>}
        </>;
        return interactive ? <button type="button" key={square} className={className}
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
    {start && end && <svg className="arrow" viewBox="0 0 800 800" aria-hidden="true">
      <defs><marker id={markerId} markerWidth="3.6" markerHeight="3.6" refX="2.8" refY="1.8" orient="auto">
        <path d="M0,0 L3.6,1.8 L0,3.6 Z" fill="currentColor" />
      </marker></defs>
      <line x1={start.x} y1={start.y} x2={end.x - Math.cos(angle) * 22} y2={end.y - Math.sin(angle) * 22}
        stroke="currentColor" strokeWidth="17" strokeLinecap="round" markerEnd={`url(#${markerId})`} />
    </svg>}
    {/* The dragged piece follows the pointer above everything else, so it is drawn on the page body. */}
    {dragging && draggedPiece && createPortal(<span aria-hidden="true" className="pc drag-ghost"
      style={{ left: dragging.x, top: dragging.y, width: dragging.size, height: dragging.size }}>
      <img src={image(draggedPiece.color, draggedPiece.type)} alt="" draggable={false} /></span>, document.body)}
  </div>;
}
