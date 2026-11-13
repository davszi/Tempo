import { Chess, type Square } from "chess.js";

export function positionAt(moves: string[], ply: number) {
  const game = new Chess();
  moves.slice(0, ply).forEach((move) => game.move(move));
  return game;
}

export function suggestedMove(moves: string[], ply: number) {
  if (ply >= moves.length) return null;
  return positionAt(moves, ply).move(moves[ply]);
}

// This demo checks the prescribed line locally. Real sessions belong to the backend.
export function advanceLearning(moves: string[], ply: number, from: Square, to: Square) {
  const expected = suggestedMove(moves, ply);
  if (!expected || expected.from !== from || expected.to !== to) return ply;
  // The learner plays White; include the scripted Black reply in the next position.
  return Math.min(ply + 2, moves.length);
}
