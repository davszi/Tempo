import { useSyncExternalStore } from "react";
import type { Side } from "./practiceApi";

/** An unfinished Learning lesson, kept in this browser so the player can continue it later. */
export type LessonProgress = { ply: number; total: number; side: Side; at: number };
type Saved = Record<string, LessonProgress>;

const KEY = "tempo-lesson-progress";
const listeners = new Set<() => void>();
let cache: Saved = read();

function read(): Saved {
  try { return JSON.parse(localStorage.getItem(KEY) || "{}") as Saved; } catch { return {}; }
}
function write(next: Saved) {
  cache = next;
  try { localStorage.setItem(KEY, JSON.stringify(next)); } catch { /* storage unavailable: keep it in memory */ }
  listeners.forEach((listener) => listener());
}

export function saveProgress(lineId: number, progress: LessonProgress) {
  write({ ...cache, [lineId]: progress });
}
export function clearProgress(lineId: number) {
  if (!(lineId in cache)) return;
  const next = { ...cache };
  delete next[lineId];
  write(next);
}
export function useProgress() {
  return useSyncExternalStore((listener) => { listeners.add(listener); return () => listeners.delete(listener); }, () => cache);
}
