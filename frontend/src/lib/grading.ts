import type { Grading } from "./practiceApi.ts";

/** Browser move times are capped at one hour before they are sent; the rule caps them again at 20 s. */
export const MAX_RESPONSE_MS = 3_600_000;

const plural = (n: number, word: string) => `${n} ${word}${n === 1 ? "" : "s"}`;
const paceWords: Record<Grading["band"], string> = { fast: "fast", normal: "steady", slow: "slow", very_slow: "very slow" };

/**
 * Plain-language reason for a review's grade, from the backend's grading breakdown
 * (docs/topics/session-grading, section 3).
 */
export function gradeExplanation(grading: Grading) {
  const pace = grading.mean_ms == null ? ""
    : ` On the moves you played without a mistake you averaged ${(grading.mean_ms / 1000).toFixed(1)} s (${paceWords[grading.band]}).`;
  if (grading.mistakes > grading.limit) {
    return `${plural(grading.mistakes, "mistake")} in ${grading.moves} moves. A line this long allows at most ${grading.limit}, so this review counts as Again.`;
  }
  if (grading.mistakes > 0 && grading.mistakes === grading.limit) {
    return `${plural(grading.mistakes, "mistake")} in ${grading.moves} moves, the most this line allows, so it is Hard.${pace}`;
  }
  if (grading.mistakes > 0) {
    return `${plural(grading.mistakes, "mistake")} in ${grading.moves} moves, within the limit of ${grading.limit}.${pace}`;
  }
  return `No mistakes in ${grading.moves} moves.${pace}`;
}
