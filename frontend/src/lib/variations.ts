import { Chess } from "chess.js";

export type VariationLine = {
  line_id: number;
  opening_family: string;
  name: string;
  eco: string;
  moves_uci: string;
  learned: boolean;
};

export type VariationGroups<T extends VariationLine> = {
  /** Lines of the same family that extend the current line move by move. */
  continuations: T[];
  /** Every other line of the same family, in opening-tree order. */
  others: T[];
  /** The suggested next line: the shortest unlearned continuation, else the shortest unlearned line of the family. */
  next: T | null;
};

const plies = (line: VariationLine) => line.moves_uci.split(" ").length;
const treeOrder = (a: VariationLine, b: VariationLine) => a.moves_uci.localeCompare(b.moves_uci) || a.name.localeCompare(b.name);

export function variationLabel(line: VariationLine) {
  const prefix = `${line.opening_family}: `;
  if (line.name.startsWith(prefix)) return line.name.slice(prefix.length);
  return line.name === line.opening_family ? "Main line" : line.name;
}

export function groupVariations<T extends VariationLine>(lines: T[], current: T): VariationGroups<T> {
  const family = lines.filter((line) => line.opening_family === current.opening_family && line.line_id !== current.line_id);
  const continuations = family.filter((line) => line.moves_uci.startsWith(`${current.moves_uci} `)).sort(treeOrder);
  const extending = new Set(continuations.map((line) => line.line_id));
  const others = family.filter((line) => !extending.has(line.line_id)).sort(treeOrder);
  const shortestUnlearned = (candidates: T[]) => candidates.filter((line) => !line.learned)
    .sort((a, b) => plies(a) - plies(b) || treeOrder(a, b))[0];
  return { continuations, others, next: shortestUnlearned(continuations) ?? shortestUnlearned(others) ?? null };
}

/** The moves a continuation adds after the current line, in numbered SAN, for example "3. d4 d6 4. c4". */
export function addedMoves(current: VariationLine, line: VariationLine) {
  const start = plies(current);
  const game = new Chess();
  line.moves_uci.split(" ").forEach((move) => game.move(move));
  const san = game.history().slice(start);
  return san.map((move, index) => {
    const ply = start + index;
    const number = Math.floor(ply / 2) + 1;
    if (ply % 2 === 0) return `${number}. ${move}`;
    return index === 0 ? `${number}… ${move}` : move;
  }).join(" ");
}
