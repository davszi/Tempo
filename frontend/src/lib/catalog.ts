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

export type OpeningSort = "easy" | "popular";

export const openingTypes = [
  ["gambit", "Gambits"], ["defense", "Defenses"],
  ["attack", "Attacks"], ["system", "Systems"], ["open", "Open Games"],
  ["semi-open", "Semi-Open Games"], ["closed", "Closed Games"],
  ["flank", "Flank Openings"],
] as const;
export type OpeningType = typeof openingTypes[number][0];
export const allOpeningTypes = openingTypes.map(([type]) => type);

const namePatterns = {
  gambit: /\bgambits?\b/i,
  defense: /\bdefen[cs]es?\b/i,
  attack: /\battacks?\b/i,
  system: /\bsystems?\b/i,
};

export function playerMoveCount(line: OpeningLine) {
  const plies = moves(line).length;
  return line.family_side === "white" ? Math.ceil(plies / 2) : Math.floor(plies / 2);
}

export function linesByType(family: Family, types: readonly OpeningType[]) {
  if (types.length === allOpeningTypes.length) return family.lines;
  const byId = new Map(family.all.map((line) => [line.line_id, line]));
  return family.lines.filter((line) => types.some((type) => {
    if (type === "open" || type === "semi-open" || type === "closed" || type === "flank") {
      const [white, black] = moves(line);
      if (type === "open") return white === "e2e4" && black === "e7e5";
      if (type === "semi-open") return white === "e2e4" && !!black && black !== "e7e5";
      if (type === "closed") return white === "d2d4" && black === "d7d5";
      return white !== "e2e4" && white !== "d2d4";
    }
    const pattern = namePatterns[type];
    if (pattern.test(family.name)) return true;
    let ancestor: OpeningLine | undefined = line;
    while (ancestor) {
      if (pattern.test(ancestor.name)) return true;
      ancestor = ancestor.parent_line_id === null ? undefined : byId.get(ancestor.parent_line_id);
    }
    return false;
  }));
}

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
