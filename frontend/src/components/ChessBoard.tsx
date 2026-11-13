import { useId } from "react";
import { Chess, type Square } from "chess.js";

const symbols: Record<string, string> = { p: "♟", n: "♞", b: "♝", r: "♜", q: "♛", k: "♚" };
const names: Record<string, string> = { p: "pawn", n: "knight", b: "bishop", r: "rook", q: "queen", k: "king" };
type MoveCoordinates = { from: Square; to: Square };
type BoardProps = {
  fen: string;
  flipped?: boolean;
  disabled?: boolean;
  arrow?: MoveCoordinates | null;
  selected?: Square | null;
  lastMove?: MoveCoordinates | null;
  onSquareClick?: (square: Square) => void;
};

export function ChessBoard({ fen, flipped = false, disabled = false, arrow, selected, lastMove, onSquareClick }: BoardProps) {
  const markerId = useId().replace(/:/g, "");
  const game = new Chess(fen);
  const files = flipped ? "hgfedcba" : "abcdefgh";
  const ranks = flipped ? "12345678" : "87654321";
  const centre = (square: Square) => ({ x: files.indexOf(square[0]) * 100 + 50, y: ranks.indexOf(square[1]) * 100 + 50 });
  const start = arrow ? centre(arrow.from) : null;
  const end = arrow ? centre(arrow.to) : null;
  const angle = start && end ? Math.atan2(end.y - start.y, end.x - start.x) : 0;
  return <div className="learning-board" role={onSquareClick ? "group" : "img"}
    aria-label={`Chessboard, ${flipped ? "Black" : "White"} at the bottom`}>
    <div className="learning-board-squares">
      {Array.from({ length: 64 }, (_, index) => {
        const row = Math.floor(index / 8), col = index % 8;
        const square = `${files[col]}${ranks[row]}` as Square;
        const piece = game.get(square);
        const className = `learning-square ${(row + col) % 2 ? "learning-square-dark" : "learning-square-light"} ${selected === square ? "learning-square-selected" : ""} ${lastMove && (lastMove.from === square || lastMove.to === square) ? "learning-square-last" : ""}`;
        const content = <>
          {col === 0 && <small className="learning-rank" aria-hidden="true">{ranks[row]}</small>}
          {row === 7 && <small className="learning-file" aria-hidden="true">{files[col]}</small>}
          {piece && <span className={`learning-piece learning-piece-${piece.color}`} aria-hidden="true">{symbols[piece.type]}</span>}
        </>;
        return onSquareClick ? <button type="button" key={square} className={className}
          aria-label={`${square}${piece ? `, ${piece.color === "w" ? "white" : "black"} ${names[piece.type]}` : ", empty"}`}
          aria-pressed={selected === square} aria-disabled={disabled}
          onClick={() => { if (!disabled) onSquareClick(square); }}>{content}</button>
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
  </div>;
}
