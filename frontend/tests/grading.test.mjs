import test from "node:test";
import assert from "node:assert/strict";
import { gradeExplanation } from "../src/lib/grading.ts";

const review = (overrides) => ({ grade: "Easy", moves: 6, mistakes: 0, limit: 1, mean_ms: 1200, band: "fast", ...overrides });

test("a review within the mistake limit says so and gives the average pace", () => {
  assert.equal(gradeExplanation(review({ mistakes: 1, limit: 2, grade: "Good", band: "normal", mean_ms: 2000 })),
    "1 mistake in 6 moves, within the limit of 2. On the moves you played without a mistake you averaged 2.0 s (steady).");
});

test("reaching the limit is explained as Hard, and more mistakes than the limit as Again", () => {
  assert.match(gradeExplanation(review({ mistakes: 1, grade: "Hard" })), /the most this line allows, so it is Hard\./);
  assert.equal(gradeExplanation(review({ mistakes: 2, grade: "Again", limit: 1 })),
    "2 mistakes in 6 moves. A line this long allows at most 1, so this review counts as Again.");
});

test("a clean review explains its pace, and a review without timed moves has no pace", () => {
  assert.equal(gradeExplanation(review({})), "No mistakes in 6 moves. On the moves you played without a mistake you averaged 1.2 s (fast).");
  assert.equal(gradeExplanation(review({ mean_ms: null })), "No mistakes in 6 moves.");
});
