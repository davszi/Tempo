import test from "node:test";
import assert from "node:assert/strict";
import { forgetSkip, markSkipped, nextDueLine, otherDueCount, pastCard, pastCards, rememberCard } from "../src/lib/reviewQueue.ts";

const NOW = Date.parse("2026-11-17T18:00:00Z");
const line = (line_id, hoursAgo) => ({ line_id, next_review_at: new Date(NOW - hoursAgo * 3_600_000).toISOString(), stability_days: 3 });
// 1 is most overdue, 4 is due in the future.
const LINES = [line(2, 5), line(1, 30), line(3, 1), line(4, -10)];

test("the next opening is the most overdue one other than the current", () => {
  assert.equal(nextDueLine(LINES, NOW, null, []), 1);
  assert.equal(nextDueLine(LINES, NOW, 1, []), 2);
});

test("openings that are not due yet are never offered", () => {
  assert.equal(nextDueLine([line(4, -10)], NOW, null, []), null);
  assert.equal(nextDueLine([line(1, 30)], NOW, 1, []), null);
});

test("skipped openings go to the back, in the order they were skipped", () => {
  assert.equal(nextDueLine(LINES, NOW, 3, [1]), 2);
  assert.equal(nextDueLine(LINES, NOW, 3, [2, 1]), 2);
  assert.equal(nextDueLine(LINES, NOW, 3, [1, 2]), 1);
  assert.equal(nextDueLine(LINES, NOW, null, [1, 2, 3]), 1);
});

test("the shared skip list moves a skipped opening back and forgets it once reviewed", () => {
  markSkipped(1);
  assert.equal(nextDueLine(LINES, NOW, 3), 2);
  forgetSkip(1);
  assert.equal(nextDueLine(LINES, NOW, 3), 1);
});

test("the count of other due openings leaves out the current one and future ones", () => {
  assert.equal(otherDueCount(LINES, NOW, 1), 2);
  assert.equal(otherDueCount(LINES, NOW, null), 3);
});

const card = (lineId, status) => ({ lineId, title: `Line ${lineId}`, side: "white", fen: "8/8/8/8/8/8/8/8 w - - 0 1", status,
  grade: status === "reviewed" ? "Good" : null, nextReviewAt: null });

test("swiping down walks back through the cards left behind, newest first", () => {
  const cards = [card(1, "reviewed"), card(2, "skipped"), card(3, "reviewed")];
  assert.equal(pastCard(1, cards).lineId, 3);
  assert.equal(pastCard(3, cards).lineId, 1);
  assert.equal(pastCard(4, cards), null);
  assert.equal(pastCard(0, cards), null);
});

test("the history keeps the last 20 cards", () => {
  for (let index = 0; index < 25; index++) rememberCard(card(100 + index, "reviewed"));
  assert.equal(pastCards().length, 20);
  assert.equal(pastCard(1).lineId, 124);
  assert.equal(pastCard(20).lineId, 105);
});
