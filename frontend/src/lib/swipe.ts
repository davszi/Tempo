/**
 * Swipe between review cards (Repeating, in the Android app; mobile/README.md): up for the next
 * opening, down for the cards before. A swipe counts when it is mostly in one direction and either
 * long enough or a quick flick.
 */
export const SWIPE_MIN_PX = 60;
export const SWIPE_SIZE_SHARE = 0.12;
export const FLICK_MIN_PX = 30;
export const FLICK_PX_PER_MS = 0.5;

export type SwipeOutcome = "up" | "down" | "left" | "cancel";

export function swipeOutcome(dx: number, dy: number, ms: number, width: number, height = width): SwipeOutcome {
  const quick = (distance: number) => distance >= FLICK_MIN_PX && distance / Math.max(ms, 1) >= FLICK_PX_PER_MS;
  if (dy < 0 && -dy >= Math.abs(dx) * 1.5) {
    return -dy >= Math.max(SWIPE_MIN_PX, height * SWIPE_SIZE_SHARE) || quick(-dy) ? "up" : "cancel";
  }
  if (dy > 0 && dy >= Math.abs(dx) * 1.5) {
    return dy >= Math.max(SWIPE_MIN_PX, height * SWIPE_SIZE_SHARE) || quick(dy) ? "down" : "cancel";
  }
  if (dx < 0 && -dx >= Math.abs(dy) * 1.5) {
    return -dx >= Math.max(SWIPE_MIN_PX, width * SWIPE_SIZE_SHARE) || quick(-dx) ? "left" : "cancel";
  }
  return "cancel";
}

/** Where the board sits while a finger drags it: follows an upward or leftward drag, resists the rest. */
export function dragOffset(dx: number, dy: number): { x: number; y: number } {
  if (Math.abs(dy) >= Math.abs(dx)) return { x: 0, y: dy < 0 ? dy : dy * 0.2 };
  return { x: dx < 0 ? dx : dx * 0.2, y: 0 };
}

// Set when a swipe starts the next review, so the new board slides in from the same side. It expires
// quickly, so a review started later by other means never slides in. Reading it does not clear it,
// because React's development mode runs state initialisers twice.
const ARRIVAL_WINDOW_MS = 3000;
let swiped: { at: number; from: "up" | "left" } | null = null;
export function markArrivedBySwipe(from: "up" | "left", now = Date.now()) { swiped = { at: now, from }; }
export function arrivedBySwipe(now = Date.now()): "up" | "left" | null {
  return swiped && now - swiped.at <= ARRIVAL_WINDOW_MS ? swiped.from : null;
}
