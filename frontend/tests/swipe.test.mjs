import test from "node:test";
import assert from "node:assert/strict";
import { arrivedBySwipe, dragOffset, markArrivedBySwipe, swipeOutcome } from "../src/lib/swipe.ts";

const WIDTH = 360;   // a phone-sized board

test("a long left swipe moves to the next review", () => {
  assert.equal(swipeOutcome(-120, 10, 400, WIDTH), "next");
});

test("a short, quick left flick also moves on", () => {
  assert.equal(swipeOutcome(-40, 5, 60, WIDTH), "next");
});

test("short slow drags, right swipes and mostly vertical moves do nothing", () => {
  assert.equal(swipeOutcome(-40, 0, 400, WIDTH), "cancel");
  assert.equal(swipeOutcome(150, 0, 200, WIDTH), "cancel");
  assert.equal(swipeOutcome(-80, 90, 200, WIDTH), "cancel");
  assert.equal(swipeOutcome(0, 0, 0, WIDTH), "cancel");
});

test("a wide board needs a quarter of its width for a slow swipe", () => {
  assert.equal(swipeOutcome(-120, 0, 600, 600), "cancel");
  assert.equal(swipeOutcome(-160, 0, 600, 600), "next");
});

test("the board follows a left drag, resists a right one and ignores scrolling", () => {
  assert.equal(dragOffset(-50, 10), -50);
  assert.equal(dragOffset(50, 10), 10);
  assert.equal(dragOffset(-20, 60), 0);
});

test("only a review started by a swipe a moment ago slides in", () => {
  assert.equal(arrivedBySwipe(0), false);
  markArrivedBySwipe(10_000);
  assert.equal(arrivedBySwipe(10_500), true);
  assert.equal(arrivedBySwipe(20_000), false);
});
