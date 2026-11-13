# Opening library

## Scope

This record owns TEMPO's opening library: the list of real named lines that
synthetic clients study, how each line is classified, and how the side
(White or Black) of each opening family was decided and checked. The
simulator that uses the library is described in
[FSRS training on synthetic clients](../fsrs-training/fsrs-training.md).

Status: implemented in `ml/ml_1000bots/openings/`. The side labels are a proposal
from the ML work; the team has not accepted them yet (see
[open questions](#open-questions)).

## Source

| Item | Value |
|---|---|
| Source | [lichess-org/chess-openings](https://github.com/lichess-org/chess-openings), files `a.tsv` to `e.tsv` from `master`, fetched 2026-11-11 |
| Licence | CC0 (public domain) |
| Local copy | `ml/ml_1000bots/openings/lichess_openings.tsv`, 3,865 lines plus header, sha256 `ea20307b7d5edba152ca69f2f9c8f92cb2260169d53e3596ea6fadbeca916b18` |
| Columns | `eco`, `name`, `pgn` (no side information) |

Opening names and moves are used as Lichess publishes them; they were not
checked against other opening references.

## Classification

`python ml/ml_1000bots/openings/classify.py` writes
`ml/ml_1000bots/openings/lichess_openings_classified.csv` (sha256
`2d9c59dcea685032e79218df25ade2b017d8b2111e0957440ff9e57fd9f5e69b`). The
column meanings are documented at the top of `classify.py`. In short:

- **Hierarchy**: ECO letter (A–E) → family (name before `:`, 140 families
  after folding `", with …"` suffixes into a `family_qualifier` column) →
  variation → subvariation.
- **Length**: `plies`, `white_moves`, `black_moves`, `last_mover`.
- **Side**: `base_opening`, `family_side`, and the game evidence columns
  `side_in_games`, `side_ratio`, `n_games`.
- `name` and `pgn` are unchanged from Lichess. 688 names occur with more than
  one move order (transpositions); no move sequence occurs twice. A name is
  therefore not a unique line key.

### Side of a family

`family_side` is the side whose repertoire choice the family is, set by hand
for every base opening in `classify.py`:

- Sicilian Defense → black, Ruy Lopez → white.
- Catch-all families follow their first named move: Queen's Pawn Game →
  white (1.d4), Indian Defense → black (1...Nf6).
- `Accepted` / `Declined` families take the side of their base gambit, i.e.
  the gambit player: King's Gambit Accepted → white, Latvian Gambit Accepted
  → black.
- `both` only for the Four Knights Game, which needs 3.Nc3 from White and
  3...Nf6 from Black.

Result: 69 white, 70 black and 1 both family.

**Rejected alternatives:**

- *Side of the last move of the family's shortest line.* It differs from
  `family_side` for 21 families: 12 Accepted/Declined families and 9 others
  where the last move does not name the opening (Amsterdam Attack, Colle
  System, Creepy Crawly Formation, Four Knights Game, King's Indian Defense,
  Lion Defense, Old Indian Defense, Pterodactyl Defense, Rat Defense). For
  example, the shortest King's Indian Defense line ends with White's 3.Nc3.
- *Accepted/Declined belong to the responder.* Real games contradicted this
  for 9 of 9 families with clear evidence, for example King's Gambit Accepted
  (side ratio 3.18 towards White). The base-gambit rule agreed with all of
  them.

**Evidence from real games.** `ml/ml_1000bots/openings/side_evidence.py` measures
which side's players keep returning to a family. For each family and colour,
it takes P(a player's next game with that colour is the same family) divided
by the family's overall share. `side_ratio` = white value / black value:
≥ 2 means white, ≤ 0.5 means black, and anything in between means both. A
verdict needs ≥ 100 game pairs on each side.

| Input | Value |
|---|---|
| Dataset | [Lichess/standard-chess-games](https://huggingface.co/datasets/Lichess/standard-chess-games) on Hugging Face |
| Files | `year=2025/month=06/train-00000-of-00065.parquet` (sha256 `63b42b6d…19be8a7`) and `year=2024/month=01/train-0000{0..5}-of-00421.parquet` |
| Games | 2,806,195 after dropping bot games; days 2024-01-01 and 2025-06-01 |
| Renamed opening | "Russian Game" (2024 name) read as "Petrov's Defense" |

Results (in `family_side_evidence.csv` and the classified CSV):

- 93 families have a clear verdict; 92 agree with `family_side`.
- 29 families are played regularly by both sides (e.g. Slav Defense,
  King's Indian Defense, Italian Game).
- 18 families (26 lines) have too few games and rely on the hand label only;
  each was checked by hand.
- The two days were also scored separately. The clear verdicts agreed with
  `family_side` on each day, and no family flipped between white and black.
  Seven borderline families moved between a side and `both`.

The one disagreement is **Benko Gambit Declined** (6 lines, label black, games
white with ratio 2.34 from 142 pairs). White chooses how to decline, and the
Benko player must know those lines too.

**Suggested app filter**: for a player practising side X, show lines where
`family_side == X` or `side_in_games` is X or `both`.

### Checks

Run on 2026-11-11 with Python 3.13.3 and python-chess 1.11.2:

- All 3,865 lines replayed legally with python-chess. `plies`,
  `white_moves`, `black_moves` and `last_mover` match the replay (0 problems).
- `family` + `family_qualifier` + `variation` + `subvariation` rebuild every
  original name (0 mismatches).
- The white and black hand lists do not overlap; `classify.py` asserts this,
  and that every base opening has a side.
- Row order, names, moves and ECO codes are identical to the source TSV.

## Open questions

- The team should confirm the side labels. Most worth a second look:
  - the 9 hand-labelled families listed under rejected alternatives;
  - Queen's Gambit Declined and Accepted, which are labelled white by the
    base-gambit rule although opening books call them Black's defences;
  - Benko Gambit Declined.
- Whether the app uses `family_side` alone or with `side_in_games`, as in
  the suggested filter above.
