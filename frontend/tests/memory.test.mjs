import test from "node:test";
import assert from "node:assert/strict";
import { DAY, dayStart, dueInfo, recallLevel, timeline } from "../src/lib/memory.ts";
import { buildFamilies, closestLines, lineLabel, sharedPlies } from "../src/lib/catalog.ts";

const noon = new Date(2026, 10, 14, 12, 0).getTime();
const at = (offsetMs) => new Date(noon + offsetMs).toISOString();

test("days until forgetting covers new, overdue, due, later-today and future lines", () => {
  assert.equal(dueInfo({ next_review_at: at(0), stability_days: null }, noon, 0.9).text, "First test ready");
  const overdue = dueInfo({ next_review_at: at(-2 * DAY), stability_days: 3 }, noon, 0.9);
  assert.equal(overdue.text, "Overdue 2 days");
  assert.equal(overdue.tone, "bad");
  assert.equal(dueInfo({ next_review_at: at(-60_000), stability_days: 3 }, noon, 0.9).text, "Due now");
  assert.equal(dueInfo({ next_review_at: at(60 * 60_000), stability_days: 3 }, noon, 0.9).text, "Due later today");
  const later = dueInfo({ next_review_at: at(5 * DAY), stability_days: 9 }, noon, 0.9);
  assert.equal(later.text, "5 days left");
  assert.match(later.long, /5 days until recall drops below 90%/);
});

test("recall bands compare with the target", () => {
  assert.equal(recallLevel(0.93, 0.9), "ok");
  assert.equal(recallLevel(0.85, 0.9), "mid");
  assert.equal(recallLevel(0.7, 0.9), "low");
});

test("the timeline puts overdue lines on today and counts lines beyond the window", () => {
  const lines = [
    { next_review_at: at(-3 * DAY), stability_days: 2 },
    { next_review_at: at(-60_000), stability_days: 2 },
    { next_review_at: at(DAY), stability_days: 4 },
    { next_review_at: at(40 * DAY), stability_days: 60 },
  ];
  const { days, later } = timeline(lines, noon, 30);
  assert.equal(days.length, 30);
  assert.equal(days[0].day, dayStart(noon));
  assert.deepEqual(days[0].lines, [0, 1]);
  assert.equal(days[0].late, 1);
  assert.deepEqual(days[1].lines, [2]);
  assert.equal(later, 1);
});

const line = (line_id, opening_family, family_side, name, moves_uci, learnable = true) =>
  ({ line_id, opening_family, family_side, name, eco: "B02", moves_uci, parent_line_id: null, learnable, learned: false });

test("families keep only learnable lines, take their side from the catalog and label variations", () => {
  const catalog = [
    line(1, "Alekhine Defense", "black", "Alekhine Defense", "e2e4 g8f6", false),
    line(2, "Alekhine Defense", "black", "Alekhine Defense: Four Pawns Attack", "e2e4 g8f6 e4e5 f6d5 d2d4 d7d6 c2c4 d5b6 f2f4"),
    line(3, "Alekhine Defense", "black", "Alekhine Defense: Exchange Variation", "e2e4 g8f6 e4e5 f6d5 d2d4 d7d6 c2c4 d5b6 e5d6"),
    line(4, "Alekhine Defense", "black", "Alekhine Defense: Brooklyn Variation", "e2e4 g8f6 e4e5 f6g8 d2d4 d7d6 g1f3"),
    line(5, "Italian Game", "white", "Italian Game", "e2e4 e7e5 g1f3 b8c6 f1c4 f8c5 c2c3"),
  ];
  const families = buildFamilies(catalog);
  assert.deepEqual(families.map((family) => [family.name, family.side, family.lines.length]), [["Alekhine Defense", "black", 3], ["Italian Game", "white", 1]]);
  assert.equal(families[0].root.line_id, 1, "the shortest line of the family is its preview");
  assert.equal(lineLabel(catalog[1]), "Four Pawns Attack");
  assert.equal(lineLabel(catalog[4]), "Main line");
  assert.equal(sharedPlies(catalog[1].moves_uci, catalog[2].moves_uci), 8);
  assert.deepEqual(closestLines(catalog[1], families[0].lines).map((item) => [item.line.line_id, item.shared]), [[3, 8], [4, 3]]);
});
