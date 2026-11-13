import test from "node:test";
import assert from "node:assert/strict";
import { addedMoves, groupVariations, variationLabel } from "../src/lib/variations.ts";

const line = (line_id, name, moves_uci, learned = false, opening_family = "Alekhine Defense") =>
  ({ line_id, opening_family, name, eco: "B03", moves_uci, learned });

const main = line(1, "Alekhine Defense", "e2e4 g8f6 e4e5 f6d5 d2d4");
const catalog = [
  main,
  line(2, "Alekhine Defense", "e2e4 g8f6 e4e5 f6d5 d2d4 d7d6"),
  line(3, "Alekhine Defense: Four Pawns Attack", "e2e4 g8f6 e4e5 f6d5 d2d4 d7d6 c2c4 d5b6 f2f4"),
  line(4, "Alekhine Defense: Balogh Variation", "e2e4 g8f6 e4e5 f6d5 d2d4 d7d6 f1c4", true),
  line(5, "Alekhine Defense: Brooklyn Variation", "e2e4 g8f6 e4e5 f6g8"),
  line(6, "Alekhine Defense: Buckley Attack", "e2e4 g8f6 e4e5 f6d5 b1a3"),
  line(7, "Sicilian Defense", "e2e4 c7c5", false, "Sicilian Defense"),
];

test("variation labels drop the family prefix and name the bare family the main line", () => {
  assert.equal(variationLabel(catalog[2]), "Four Pawns Attack");
  assert.equal(variationLabel(main), "Main line");
});

test("continuations extend the current line and the rest of the family is listed separately", () => {
  const { continuations, others, next } = groupVariations(catalog, main);
  assert.deepEqual(continuations.map((l) => l.line_id), [2, 3, 4]);
  assert.deepEqual(others.map((l) => l.line_id).sort(), [5, 6]);
  assert.ok(![...continuations, ...others].some((l) => l.line_id === 1 || l.line_id === 7));
  assert.equal(next?.line_id, 2, "the shortest unlearned continuation is suggested next");
});

test("when every continuation is learned the next suggestion comes from the other variations", () => {
  const learned = catalog.map((l) => [2, 3, 4].includes(l.line_id) ? { ...l, learned: true } : l);
  assert.equal(groupVariations(learned, main).next?.opening_family, "Alekhine Defense");
  assert.equal(groupVariations(learned, main).continuations.find((l) => !l.learned), undefined);
  const allLearned = learned.map((l) => ({ ...l, learned: true }));
  assert.equal(groupVariations(allLearned, main).next, null);
});

test("added moves are numbered from where the current line stops", () => {
  assert.equal(addedMoves(main, catalog[1]), "3… d6");
  assert.equal(addedMoves(main, catalog[2]), "3… d6 4. c4 Nb6 5. f4");
});
