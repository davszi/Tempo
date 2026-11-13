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

function movesFrom(moves: string[], start: number) {
  const history = positionAt(moves, moves.length).history();
  return history.slice(start).map((san, offset) => {
    const ply = start + offset;
    const number = Math.floor(ply / 2) + 1;
    if (ply % 2 === 0) return `${number}.${san}`;
    return offset === 0 ? `${number}…${san}` : san;
  }).join(" ");
}

type NamedLine = { line_id: number; name: string; moves_uci: string };

// For lines that share a name, the moves from where each one first differs from the others.
export function distinguishingMoves(lines: NamedLine[]) {
  const groups = new Map<string, string[][]>();
  const split = new Map(lines.map((line) => [line.line_id, line.moves_uci.split(" ")]));
  for (const line of lines) {
    const group = groups.get(line.name) ?? [];
    group.push(split.get(line.line_id)!);
    groups.set(line.name, group);
  }
  const labels = new Map<number, string>();
  for (const line of lines) {
    const moves = split.get(line.line_id)!;
    const others = groups.get(line.name)!.filter((other) => other !== moves);
    if (others.length === 0) continue;
    const start = Math.min(...others.map((other) => {
      let ply = 0;
      while (ply < moves.length && moves[ply] === other[ply]) ply++;
      return Math.min(ply, moves.length - 1);
    }));
    labels.set(line.line_id, movesFrom(moves, start));
  }
  return labels;
}

// This demo checks the prescribed line locally. Real sessions belong to the backend.
export function advanceLearning(moves: string[], ply: number, from: Square, to: Square) {
  const expected = suggestedMove(moves, ply);
  if (!expected || expected.from !== from || expected.to !== to) return ply;
  // The learner plays White; include the scripted Black reply in the next position.
  return Math.min(ply + 2, moves.length);
}
