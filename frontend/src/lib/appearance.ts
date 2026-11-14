import { createContext, useContext } from "react";
import pieceData from "../assets/pieces.json";

/* Themes colour the app, the board and the pieces. Each theme lists [dark, light] colours for White's
   pieces and for Black's; the CSS variables for the rest of the app live in styles.css. */
export const THEMES = [
  { id: "forest", name: "Forest", note: "The calm TEMPO green", board: ["#ecf1e8", "#7e9c85"], pieces: { w: ["#1d3527", "#fbfaf1"], b: ["#1f3a2c", "#cfe3d6"] } },
  { id: "walnut", name: "Walnut", note: "Classic wooden board", board: ["#f0d9b5", "#b58863"], pieces: { w: ["#3b2a1c", "#fff8ec"], b: ["#3a2617", "#e8c9a4"] } },
  { id: "ocean", name: "Ocean", note: "Cool blue, warm arrows", board: ["#e2edf3", "#6f9cb4"], pieces: { w: ["#14304a", "#f7fbff"], b: ["#133049", "#bcd9ec"] } },
  { id: "blossom", name: "Blossom", note: "Soft rose and teal", board: ["#f6e6ec", "#c88da2"], pieces: { w: ["#4a2434", "#fff9fb"], b: ["#4a1d33", "#f2c3d4"] } },
  { id: "midnight", name: "Midnight", note: "Dark mode for late study", board: ["#c7d1e4", "#5b6f99"], pieces: { w: ["#1d2638", "#eef2ff"], b: ["#121a2b", "#9fb4e8"] } },
  { id: "arcade", name: "Arcade", note: "Dark with a neon edge", board: ["#d9d5e8", "#6c6788"], pieces: { w: ["#1f1d28", "#f7fff0"], b: ["#1b1a24", "#c9c3e0"] } },
  { id: "mono", name: "Mono", note: "Ink on paper, no colour", board: ["#f1f1f1", "#9a9a9a"], pieces: { w: ["#111111", "#ffffff"], b: ["#141414", "#e6e6e6"] } },
  { id: "tournament", name: "Tournament", note: "Club green and cream", board: ["#eff0d6", "#76985a"], pieces: { w: ["#23301c", "#fffff6"], b: ["#262b22", "#d8e6c6"] } },
  { id: "royal", name: "Royal", note: "Violet with gold arrows", board: ["#ece3f7", "#9077c0"], pieces: { w: ["#2c1f4a", "#fffbef"], b: ["#2b1c4d", "#e6d28f"] } },
] as const;
export type ThemeId = typeof THEMES[number]["id"];

/* Piece sets from the Lichess project. Every colour in each SVG was turned into a 0-1 shade at build
   time (%%shade%%); here the shade is mixed between the theme's dark and light piece colours. */
export const PIECE_SETS = [
  { id: "cburnett", name: "Classic", note: "Clean tournament shapes" },
  { id: "merida", name: "Merida", note: "Traditional book style" },
  { id: "chessnut", name: "Chessnut", note: "Crisp modern outlines" },
  { id: "spatial", name: "Spatial", note: "Soft modern shading" },
  { id: "celtic", name: "Celtic", note: "Tall carved silhouettes" },
  { id: "rhosgfx", name: "Chunky", note: "Bold and friendly" },
] as const;
export type PieceSetId = typeof PIECE_SETS[number]["id"];
export const PIECE_CREDITS = "Piece sets from the Lichess project, recoloured: Classic by Colin M.L. Burnett and Merida by Armando Hernandez Marroquin (GPLv2+); Chessnut by Alexis Luengas (Apache 2.0); Spatial and Celtic by Maurizio Monge (MIT); Chunky by RhosGFX (CC0).";

const svgs = pieceData as Record<string, Record<string, string>>;
const hex = (value: string) => [1, 3, 5].map((i) => parseInt(value.slice(i, i + 2), 16));
const mix = (a: string, b: string, t: number) => "#" + hex(a).map((v, i) => Math.round(v + (hex(b)[i] - v) * t).toString(16).padStart(2, "0")).join("");
const cache = new Map<string, string>();

/** A data URI for one piece, e.g. code "wK", drawn in the given theme's colours. */
export function pieceImage(set: PieceSetId, code: string, themeId: ThemeId) {
  const key = `${themeId}|${set}|${code}`;
  let uri = cache.get(key);
  if (!uri) {
    const theme = THEMES.find((t) => t.id === themeId) ?? THEMES[0];
    const [dark, light] = theme.pieces[code[0] as "w" | "b"];
    const svg = svgs[set][code].replace(/%%([\d.]+)%%/g, (_, shade: string) => mix(dark, light, Number(shade)));
    uri = `data:image/svg+xml,${encodeURIComponent(svg)}`;
    cache.set(key, uri);
  }
  return uri;
}

export type Appearance = { theme: ThemeId; pieces: PieceSetId };
const KEY = "tempo-appearance";
export function loadAppearance(): Appearance {
  try {
    const saved = JSON.parse(localStorage.getItem(KEY) || "{}");
    return {
      theme: THEMES.some((t) => t.id === saved.theme) ? saved.theme : "forest",
      pieces: PIECE_SETS.some((p) => p.id === saved.pieces) ? saved.pieces : "cburnett",
    };
  } catch { return { theme: "forest", pieces: "cburnett" }; }
}
export function storeAppearance(value: Appearance) {
  try { localStorage.setItem(KEY, JSON.stringify(value)); } catch { /* storage unavailable */ }
}
export const AppearanceContext = createContext<Appearance>({ theme: "forest", pieces: "cburnett" });
export const useAppearance = () => useContext(AppearanceContext);
