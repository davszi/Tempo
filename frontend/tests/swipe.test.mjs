import test from "node:test";
import assert from "node:assert/strict";
import { arrivedBySwipe, dragOffset, markArrivedBySwipe, swipeOutcome } from "../src/lib/swipe.ts";

const SIZE = 330;   // a phone-sized board

test("a long upward swipe moves on, and so does a long left swipe", () => {
  assert.equal(swipeOutcome(8, -120, 400, SIZE), "up");
  assert.equal(swipeOutcome(-120, 10, 400, SIZE), "left");
});

test("a short, quick flick also moves on", () => {
  assert.equal(swipeOutcome(4, -40, 60, SIZE), "up");
  assert.equal(swipeOutcome(-40, 5, 60, SIZE), "left");
});

test("a long or quick downward swipe goes back", () => {
  assert.equal(swipeOutcome(5, 150, 300, SIZE), "down");
  assert.equal(swipeOutcome(0, 40, 50, SIZE), "down");
  assert.equal(swipeOutcome(0, 40, 400, SIZE), "cancel");
});

test("short slow drags, right swipes and diagonal moves do nothing", () => {
  assert.equal(swipeOutcome(0, -40, 400, SIZE), "cancel");
  assert.equal(swipeOutcome(150, 0, 200, SIZE), "cancel");
  assert.equal(swipeOutcome(-80, -90, 200, SIZE), "cancel");
  assert.equal(swipeOutcome(0, 0, 0, SIZE), "cancel");
});

test("a full-screen card needs about an eighth of its height for a slow swipe", () => {
  assert.equal(swipeOutcome(0, -70, 600, 360, 700), "cancel");
  assert.equal(swipeOutcome(0, -90, 600, 360, 700), "up");
  assert.equal(swipeOutcome(0, -140, 900, 360, 704), "up");   // the slow swipe that fell short on the phone
});

test("the board follows an upward or leftward drag and resists the opposite ways", () => {
  assert.deepEqual(dragOffset(5, -50), { x: 0, y: -50 });
  assert.deepEqual(dragOffset(-50, 10), { x: -50, y: 0 });
  assert.deepEqual(dragOffset(0, 50), { x: 0, y: 10 });
  assert.deepEqual(dragOffset(50, 10), { x: 10, y: 0 });
});

test("only a review started by a swipe a moment ago slides in, from the side it was swiped", () => {
  assert.equal(arrivedBySwipe(0), null);
  markArrivedBySwipe("up", 10_000);
  assert.equal(arrivedBySwipe(10_500), "up");
  assert.equal(arrivedBySwipe(20_000), null);
});
