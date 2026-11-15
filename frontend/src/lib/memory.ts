/* What the player sees about a learned line's memory. "Days until you forget" (OPEN.md product to-do 1)
   is defined as the days until the scheduled review: next_review_at - now, the moment the predicted
   recall falls to the scheduler's target (90% by default). */
export const DAY = 86_400_000;

export const dayStart = (time: number) => { const day = new Date(time); day.setHours(0, 0, 0, 0); return day.getTime(); };
export const dayDiff = (a: number, b: number) => Math.round((dayStart(a) - dayStart(b)) / DAY);
const plural = (n: number, word: string) => `${n} ${word}${n === 1 ? "" : "s"}`;

type Memory = { next_review_at: string; stability_days: number | null };
export type Tone = "" | "warn" | "bad" | "plain";
export type DueInfo = { text: string; long: string; tone: Tone };

export const dueAt = (line: Memory) => Date.parse(line.next_review_at);
export const isDue = (line: Memory, now: number) => dueAt(line) <= now;

export function dueInfo(line: Memory, now: number, target: number): DueInfo {
  const due = dueAt(line), days = dayDiff(due, now), percent = Math.round(target * 100);
  if (line.stability_days == null) {
    return { text: "First test ready", long: "Learned, not tested yet. The first recall test starts its memory clock.", tone: "" };
  }
  if (days < 0) return { text: `Overdue ${plural(-days, "day")}`, long: `Overdue by ${plural(-days, "day")}: recall is already below ${percent}%.`, tone: "bad" };
  if (due <= now) return { text: "Due now", long: `Due today: recall has reached ${percent}%.`, tone: "warn" };
  if (days === 0) return { text: "Due later today", long: `Recall drops to ${percent}% later today.`, tone: "warn" };
  return { text: `${plural(days, "day")} left`, long: `≈ ${plural(days, "day")} until recall drops below ${percent}%.`, tone: "plain" };
}

/** Colour band for a recall value: at or above target, within 10 points of it, or lower. */
export function recallLevel(recall: number, target: number) {
  return recall >= target ? "ok" : recall >= target - 0.1 ? "mid" : "low";
}

export type TimelineDay = { index: number; day: number; lines: number[]; late: number };

/** Reviews per day for the next `count` days; day 0 also holds everything overdue. */
export function timeline<T extends Memory>(lines: T[], now: number, count = 30) {
  const today = dayStart(now);
  const days = Array.from({ length: count }, (_, index) => {
    const day = today + index * DAY;
    const due = lines.map((line, i) => ({ line, i })).filter(({ line }) =>
      index === 0 ? dueAt(line) < day + DAY : dayStart(dueAt(line)) === day);
    return { index, day, lines: due.map(({ i }) => i), late: index === 0 ? due.filter(({ line }) => dueAt(line) < today).length : 0 };
  });
  const later = lines.filter((line) => dueAt(line) >= today + count * DAY).length;
  return { days, later };
}
