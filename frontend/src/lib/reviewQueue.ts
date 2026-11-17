import { dueAt, isDue } from "./memory.ts";

/**
 * Which due opening to review next when the player swipes on (Repeating, in the Android app).
 * Openings skipped earlier in this visit go to the back of the queue; otherwise the most overdue
 * comes first. A skipped opening is not graded: it stays due until it is reviewed.
 */
type QueueLine = { line_id: number; next_review_at: string; stability_days: number | null };

const skipped: number[] = [];

export function markSkipped(lineId: number) {
  forgetSkip(lineId);
  skipped.push(lineId);
}

export function forgetSkip(lineId: number) {
  const index = skipped.indexOf(lineId);
  if (index >= 0) skipped.splice(index, 1);
}

export function nextDueLine(lines: QueueLine[], now: number, currentId: number | null,
  skippedIds: readonly number[] = skipped): number | null {
  const order = (line: QueueLine) => skippedIds.indexOf(line.line_id);
  const due = lines.filter((line) => line.line_id !== currentId && isDue(line, now));
  due.sort((a, b) => order(a) - order(b) || dueAt(a) - dueAt(b) || a.line_id - b.line_id);
  return due[0]?.line_id ?? null;
}

export function otherDueCount(lines: QueueLine[], now: number, currentId: number | null): number {
  return lines.filter((line) => line.line_id !== currentId && isDue(line, now)).length;
}

/**
 * Cards already left behind in this visit, oldest first, so swiping down can show them again.
 * They are read-only: a skipped one can be reviewed again from its card.
 */
export type PastCard = {
  lineId: number; title: string; side: "white" | "black" | "both"; fen: string;
  status: "reviewed" | "skipped"; grade: "Again" | "Hard" | "Good" | "Easy" | null; nextReviewAt: string | null;
};
const MAX_PAST_CARDS = 20;
const past: PastCard[] = [];

export function rememberCard(card: PastCard) {
  past.push(card);
  if (past.length > MAX_PAST_CARDS) past.shift();
}

export function pastCards(): readonly PastCard[] {
  return past;
}

/** The card `stepsBack` steps behind the current one (1 = the previous card), or null. */
export function pastCard(stepsBack: number, cards: readonly PastCard[] = past): PastCard | null {
  return stepsBack >= 1 && stepsBack <= cards.length ? cards[cards.length - stepsBack] : null;
}
