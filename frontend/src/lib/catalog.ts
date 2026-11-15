import { distinguishingMoves } from "./learning.ts";
import type { FamilySide, OpeningLine } from "./practiceApi.ts";

export type Family = {
  name: string;
  side: FamilySide;
  /** Lines that can be learned (no other line extends them), in opening-tree order. */
  lines: OpeningLine[];
  /** Every catalog line of the family, used for the preview position. */
  all: OpeningLine[];
  eco: string;
  /** The family's shortest line, shown on its card. */
  root: OpeningLine;
};

const moves = (line: { moves_uci: string }) => line.moves_uci.split(" ");
const treeOrder = (a: OpeningLine, b: OpeningLine) => a.moves_uci.localeCompare(b.moves_uci) || a.name.localeCompare(b.name);

/** The variation part of a line name: "Alekhine Defense: Four Pawns Attack" becomes "Four Pawns Attack". */
export function lineLabel(line: { name: string; opening_family: string }) {
  const family = line.opening_family;
  if (line.name === family) return "Main line";
  if (line.name.startsWith(`${family}: `)) return line.name.slice(family.length + 2);
  if (line.name.startsWith(`${family} `)) return line.name.slice(family.length + 1);
  return line.name;
}

export function buildFamilies(catalog: OpeningLine[]): Family[] {
  const byName = new Map<string, OpeningLine[]>();
  for (const line of catalog) {
    const list = byName.get(line.opening_family) ?? [];
    list.push(line);
    byName.set(line.opening_family, list);
  }
  return [...byName].map(([name, all]) => {
    const lines = all.filter((line) => line.learnable).sort(treeOrder);
    const ecos = [...new Set(lines.map((line) => line.eco))].sort();
    const root = [...all].sort((a, b) => moves(a).length - moves(b).length || treeOrder(a, b))[0];
    return { name, side: all[0].family_side, lines, all, root, eco: ecos.length > 1 ? `${ecos[0]}–${ecos.at(-1)}` : ecos[0] ?? "" };
  }).filter((family) => family.lines.length > 0).sort((a, b) => a.name.localeCompare(b.name));
}

/** For learnable lines that share a name, the moves that tell them apart. */
export function variantMoves(catalog: OpeningLine[]) {
  return distinguishingMoves(catalog.filter((line) => line.learnable));
}

/** How many opening moves two lines have in common. */
export function sharedPlies(a: string, b: string) {
  const x = a.split(" "), y = b.split(" ");
  let ply = 0;
  while (ply < x.length && ply < y.length && x[ply] === y[ply]) ply++;
  return ply;
}

/** The family's other lines, closest to the current one first (most moves in common, then shortest). */
export function closestLines(current: OpeningLine, family: OpeningLine[]) {
  return family.filter((line) => line.line_id !== current.line_id)
    .map((line) => ({ line, shared: sharedPlies(current.moves_uci, line.moves_uci) }))
    .sort((a, b) => b.shared - a.shared || moves(a.line).length - moves(b.line).length || treeOrder(a.line, b.line));
}
