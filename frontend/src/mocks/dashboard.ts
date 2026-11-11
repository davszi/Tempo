import type { Opening, UserProgress } from "../types";
import { dateOffset } from "../lib/dates";
export const demoUser = { name: "Zeel", role: "Demo student" };
export const openings: Opening[] = [
  { id: "ruy-lopez", name: "Ruy Lopez" },
  { id: "italian-game", name: "Italian Game" },
  { id: "queens-gambit", name: "Queen’s Gambit" },
];
// Sample data only. This module can later be replaced by an agreed API adapter.
export function createMockProgress(): UserProgress {
  return {
    "ruy-lopez": {
      status: "completed", nextReview: dateOffset(0),
    },
    "italian-game": { status: "completed", nextReview: dateOffset(2) },
    "queens-gambit": { status: "learning", nextReview: dateOffset(4) },
  };
}
