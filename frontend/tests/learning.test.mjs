import test from "node:test";
import assert from "node:assert/strict";
import { openingLines } from "../src/data/openings.ts";
import { advanceLearning, distinguishingMoves, positionAt, suggestedMove } from "../src/lib/learning.ts";

const najdorf = "e2e4 c7c5 g1f3 d7d6 d2d4 c5d4 f3d4 g8f6 b1c3 a7a6";

test("lines sharing a name are labelled from the move where they differ", () => {
  const labels = distinguishingMoves([
    { line_id: 1, name: "English Attack", moves_uci: `${najdorf} c1e3 e7e5 d4b3 c8e6 f2f3` },
    { line_id: 2, name: "English Attack", moves_uci: `${najdorf} c1e3 e7e5 d4b3 c8e6 h2h3` },
    { line_id: 3, name: "English Attack", moves_uci: `${najdorf} c1e3 e7e5 d4b3 f8e7 f2f3` },
    { line_id: 4, name: "Zagreb Variation", moves_uci: `${najdorf} g2g3` },
  ]);
  assert.equal(labels.get(1), "7…Be6 8.f3");
  assert.equal(labels.get(2), "7…Be6 8.h3");
  assert.equal(labels.get(3), "7…Be7 8.f3");
  assert.equal(labels.has(4), false);
  assert.equal(new Set(labels.values()).size, labels.size);
});

test("every sample line has valid previews and can be learned as White", () => {
  for (const line of openingLines) {
    assert.equal(positionAt(line.moves, line.previewPly).history().length, line.previewPly);
    let ply = 0;
    while (ply < line.moves.length) {
      const before = positionAt(line.moves, ply);
      assert.equal(before.turn(), "w");
      const hint = suggestedMove(line.moves, ply);
      assert.ok(before.moves({ verbose: true }).some((move) => move.from === hint.from && move.to === hint.to));
      const next = advanceLearning(line.moves, ply, hint.from, hint.to);
      assert.ok(next > ply);
      assert.equal(positionAt(line.moves, next).history().length, next);
      ply = next;
    }
    assert.equal(ply, line.moves.length);
    assert.equal(suggestedMove(line.moves, ply), null);
  }
});

test("a legal move outside the repertoire leaves the position unchanged", () => {
  const moves = openingLines[0].moves;
  const initialFen = positionAt(moves, 0).fen();
  assert.equal(advanceLearning(moves, 0, "e2", "e3"), 0);
  assert.equal(advanceLearning(moves, 0, "d2", "d4"), 0);
  assert.equal(positionAt(moves, 0).fen(), initialFen);
});

test("the suggested move advances with the scripted reply and castling moves both pieces", () => {
  const moves = openingLines[0].moves;
  const ply = advanceLearning(moves, 0, "e2", "e4");
  assert.equal(ply, 2);
  assert.equal(positionAt(moves, ply).get("e5")?.color, "b");
  assert.equal(suggestedMove(moves, ply).san, "Nf3");
  const castle = suggestedMove(moves, 8);
  assert.equal(castle.from, "e1");
  assert.equal(castle.to, "g1");
  const finalPly = advanceLearning(moves, 8, "e1", "g1");
  const final = positionAt(moves, finalPly);
  assert.equal(final.get("g1")?.type, "k");
  assert.equal(final.get("f1")?.type, "r");
  assert.equal(advanceLearning(moves, finalPly, "e1", "g1"), finalPly);
});
