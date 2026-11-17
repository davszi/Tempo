/**
 * Swipe the board to the next review (Repeating, in the Android app; mobile/README.md).
 * A left swipe counts when it is mostly sideways and either long enough or a quick flick.
 */
export const SWIPE_MIN_PX = 60;
export const SWIPE_WIDTH_SHARE = 0.25;
export const FLICK_MIN_PX = 30;
export const FLICK_PX_PER_MS = 0.5;

export type SwipeOutcome = "next" | "cancel";

export function swipeOutcome(dx: number, dy: number, ms: number, width: number): SwipeOutcome {
  if (dx >= 0 || Math.abs(dx) < Math.abs(dy) * 1.5) return "cancel";
  const distance = -dx;
  if (distance >= Math.max(SWIPE_MIN_PX, width * SWIPE_WIDTH_SHARE)) return "next";
  if (distance >= FLICK_MIN_PX && distance / Math.max(ms, 1) >= FLICK_PX_PER_MS) return "next";
  return "cancel";
}

/** Where the board sits while a finger drags it: follows a left drag, resists a right one. */
export function dragOffset(dx: number, dy: number): number {
  if (Math.abs(dx) < Math.abs(dy)) return 0;
  return dx < 0 ? dx : dx * 0.2;
}

// Set when a swipe starts the next review, so the new board slides in from the right.
// It expires quickly, so a review started later by other means never slides in. Reading it does not
// clear it, because React's development mode runs state initialisers twice.
const ARRIVAL_WINDOW_MS = 3000;
let swipedAt = -Infinity;
export function markArrivedBySwipe(now = Date.now()) { swipedAt = now; }
export function arrivedBySwipe(now = Date.now()) {
  return now - swipedAt <= ARRIVAL_WINDOW_MS;
}
