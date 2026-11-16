"""Reproduce the numbers in the session-grading record's evidence section.

Prints (1) the catalog's line lengths in player moves, read from
backend/tempo_demo.sqlite, and (2) design arithmetic: the chance of Again
under four mistake rules and the share of Hard under two Good rules, for a
player who gets each move right with probability r, assuming independent
moves (binomial). The arithmetic is not a simulation or a measurement.

Usage, from the repository root: python -I <this file>
"""
import sqlite3
from collections import Counter
from math import comb

# Catalog: player moves per line (White plays odd plies, Black even plies)
db = sqlite3.connect("file:backend/tempo_demo.sqlite?mode=ro", uri=True)
lengths = Counter()
for side, moves in db.execute(
    "SELECT f.family_side, l.moves_uci FROM opening_lines l JOIN opening_families f USING (family_id)"
):
    plies = len(moves.split())
    lengths[(plies + 1) // 2 if side == "white" else plies // 2] += 1
print("catalog", sorted(lengths.items()), sum(lengths.values()))


def p(m, k, r):
    return comb(m, k) * (1 - r) ** k * r ** (m - k)


def again(m, r, allowed):
    return 1 - sum(p(m, k, r) for k in range(allowed + 1))


rules = {
    "any mistake": lambda m: 0,
    "0/1/2 (3 | 4-9 | 10+)": lambda m: 0 if m <= 3 else 1 if m <= 9 else 2,
    "decided 0/1/2/3 (3 | 4-7 | 8-12 | 13+)": lambda m: 0 if m <= 3 else 1 if m <= 7 else 2 if m <= 12 else 3,
    "accuracy below 70%": lambda m: max(k for k in range(m + 1) if (m - k) / m >= 0.7 - 1e-12),
}
cols = range(3, 15)
w = {m: lengths[m] for m in cols}
for name, allowed in rules.items():
    print(name, "allowed", [allowed(m) for m in cols])
    for r in (0.95, 0.9, 0.8, 0.7):
        avg = sum(again(m, r, allowed(m)) * w[m] for m in cols) / sum(w.values())
        print(f"  r={r}", [round(100 * again(m, r, allowed(m))) for m in cols], f"catalog avg {100 * avg:.1f}")

decided = rules["decided 0/1/2/3 (3 | 4-7 | 8-12 | 13+)"]
for label, good in (("strict: Good needs 0", lambda m: 0), ("decided: Good up to limit-1", lambda m: max(0, decided(m) - 1))):
    for r in (0.95, 0.9):
        hard = [round(100 * sum(p(m, k, r) for k in range(good(m) + 1, decided(m) + 1))) for m in (4, 7, 8, 10, 12, 14)]
        print(label, f"r={r}", "Hard share at M=4,7,8,10,12,14", hard)
