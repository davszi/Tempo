import test from "node:test";
import assert from "node:assert/strict";
import { SOUNDS, playSound, savedSound } from "../src/lib/sound.ts";

test("each grade has its own saved sound", () => {
  assert.equal(savedSound("Easy"), "savedEasy");
  assert.equal(savedSound("Good"), "savedGood");
  assert.equal(savedSound("Hard"), "savedHard");
  assert.equal(savedSound("Again"), "savedAgain");
});

test("every sound is short and quiet enough", () => {
  for (const [name, tones] of Object.entries(SOUNDS)) {
    const end = Math.max(...tones.map((tone) => tone.at + tone.length));
    assert.ok(end <= 0.7, `${name} lasts ${end}s`);
    for (const tone of tones) assert.ok((tone.volume ?? 0.2) <= 0.4, `${name} is too loud`);
  }
});

test("outside the app, sounds stay silent without touching audio", () => {
  assert.doesNotThrow(() => playSound("move"));
});
