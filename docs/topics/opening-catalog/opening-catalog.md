# Opening catalog structure

## Scope

This record owns the structure of TEMPO's opening catalog in the backend
database and why it has that structure: how opening families and lines are
stored, which side each family belongs to, how lines relate to each other,
and which lines a player can learn. The field-by-field schema is in
[TEMPO database schema](../database-schema/database-schema.md). Where the
library's lines come from and how their sides were first classified is in
[opening library](../opening-library/opening-library.md).

## Status

Implemented in the backend and frontend Learning flow; see
[implementation](#implementation). The catalog review was recorded on
2026-11-13. Same-family parent links and startup migration were settled with
the user, as recorded in [the worklog](../../worklog.md); the other catalog
choices still await team confirmation. See [open questions](#open-questions).
The current `ml/tempo_ml/catalog.py` reads this SQLite catalog; historical
opening-building scripts and their CSV workflow are described in
[opening library](../opening-library/opening-library.md).

## Decisions

The before/after catalog counts and references to the old schema in this
section describe the 2026-11-13 design review, not the present state of an
arbitrary local database. [Evidence](#evidence) records the original inputs,
hashes and checks. The current mechanisms are listed under
[implementation](#implementation).

### 1. A family belongs to White or Black

`opening_families.family_side` holds only `white` or `black` and is required.
`both` and empty values are removed.

- A family named "Defense" is a Black opening.
- Four Knights Game, the one family labelled `both` in that review (48 lines), becomes
  `white`.
- The backend and terminal demo can practise a line from White, Black or both
  sides. The current browser automatically uses the family side; it exposes
  no session-side selector. Session perspective belongs to
  `practice_events.side`, not to the catalog.
  Practising the other side is a learning aid for knowing the replies; it does
  not change which side a line belongs to.

**Why:** the family side states what the opening is. The Queen's Gambit is a
White opening even when a player drills Black's replies.

### 2. Remove `opening_lines.side_in_games`

A line's side is its family's side. The per-line game-evidence column is
dropped from the schema, the demo database, `Store.add_line` and the catalog
queries.

**Why:** the column is a per-family measurement from
`ml/ml_1000bots/openings/side_evidence.py` (removed 2026-11-14, at `825e9d8`) copied onto every line of the
family, so it never described individual lines. It only adds a hint that
the other side also plays a family. TEMPO does not need that hint, because the
player chooses the session side. In the demo database, 1,973 of 2,719 lines
already match their family side (48 of them are Four Knights `both`/`both`).
Of the rest, 15 are empty and the others are `both`, except the 6 lines of
Benko Gambit Declined, where games show `white` against the family's `black`.

**Rejected:** keeping the hint per family on `opening_families`. Nothing in the
app reads it.

### 3. Accepted and Declined are variations of their gambit

Every `X Accepted` and `X Declined` family is merged into family `X`. Its lines
keep their `line_id` and full name, change `family_id`, and take the parent's
side. The catalog stays flat: family → lines.

| Merged families | Lines | Parent family | Parent side |
|---|---|---|---|
| Queen's Gambit Accepted, Declined | 46, 188 | Queen's Gambit (created) | white |
| King's Gambit Accepted, Declined | 101, 27 | King's Gambit (created) | white |
| Danish Gambit Accepted | 4 | Danish Gambit (created) | white |
| Blackmar-Diemer Gambit Accepted, Declined | 22, 9 | Blackmar-Diemer Gambit (9 lines) | white |
| Benko Gambit Accepted, Declined | 10, 6 | Benko Gambit (7 lines) | black |
| Latvian Gambit Accepted | 8 | Latvian Gambit (6 lines) | black |
| Blumenfeld Countergambit Accepted | 1 | Blumenfeld Countergambit (3 lines) | black |
| Semi-Slav Defense Accepted | 1 | Semi-Slav Defense (71 lines) | black |

Twelve families are removed and three are created, so 91 families become 82.

**Why:** opening books treat Accepted and Declined as branches of the gambit,
and the side is the gambit's. The Queen's Gambit stays White, although books
call the Declined lines Black's defence. The Benko Gambit stays Black, which
also settles the one disagreement between hand labels and game evidence.

**Rejected:**

- A subfamily table. Subfamilies would carry no data of their own, since side
  comes from the family, and a gambit-only middle level would make gambits the
  only families with one. Other families split just as much (the Sicilian into
  Najdorf, Dragon and others).
- A `variation` column. Line names already carry the Lichess
  "Family: Variation, Subvariation" structure. If grouping inside families is
  needed later, it is added for every family, not only gambits.

### 4. Progress stays per line

`player_lines` keeps one review schedule per (player, line). It does not gain a
side.

**Why:** a line is remembered from its family's side. Drilling the other side
is a learning aid, not a second repertoire item.

**Rejected:** keying `player_lines` on (player, line, side).

### 5. Lines with the same name are told apart by their moves

The frontend shows each line's distinguishing move next to its name, for
example "Najdorf Variation · 6.Bg5". The database does not change. In the demo
database, 228 names are shared by 751 lines; "Sicilian Defense: Najdorf
Variation" names 5 lines.

**Rejected:** a stored `display_name` unique within a family. The move is the
information a player needs, and it is derived from `moves_uci`.

### 6. `moves_uci` is a line's permanent identity

`moves_uci` is already unique. Any catalog load upserts on it: an existing
line keeps its `line_id` and has its name, ECO code and family updated; a new
line is inserted; a line removed upstream is not deleted while a player has it
in `player_lines`. `Store.add_line` updates an existing line instead of failing
on a duplicate move sequence.

**Why:** `line_id` is what practice history and progress reference. Rebuilding
the catalog by delete and reinsert could reassign IDs and attach progress to
the wrong lines.

**Rejected:** a separate `source_key`. The Lichess source has no line ID and
names are not unique, so the key would be the move sequence again.

The repository has no catalog import script yet; this rule applies to the
first one.

### 7. Lines form a tree through `parent_line_id`

`opening_lines` gains a nullable `parent_line_id`: the longest other line of
the **same family** whose moves are a prefix of this line's moves. The
backend recomputes it whenever the catalog changes. Families stay flat; the
tree runs inside them.

In the 2026-11-13 demo database, after the merges of decision 3, 1,774 of 2,719 lines
have a parent and 945 are roots.

**Why:** the tree shows how lines branch, so lines with the same name sit at
different points and can be learned in order. Scheduling and progress do not
change. Links stay inside a family so a family's lines never hang under
another family's line.

**Rejected:** linking to the longest prefix anywhere in the catalog. It gives
1,820 lines a parent, 55 of them in another family after the merges, for
example Pterodactyl Defense lines under Modern Defense.

**Rejected for now:** a full move tree that stores each position once (7,843
distinct move prefixes against 32,511 stored moves). It would change the
scheduler and practice logic and is only worth it for per-move learning.

### 8. Only subvariations can be learned

A line can be learned only when no other line has it as `parent_line_id`. The
shorter lines become headings in the tree; their moves are practised as the
start of every subvariation below them. Learnability is derived from the tree
and not stored:

```sql
NOT EXISTS (SELECT 1 FROM opening_lines AS c WHERE c.parent_line_id = o.line_id)
```

- `Store.learning_catalog` and `Store.list_lines` return every line with a
  `learnable` flag, so headings are available for a tree view.
- `PracticeController.start_learning` refuses a heading line, and
  `MLController.initialize_progress` refuses to add one to a repertoire.
- The frontend Learning list shows only learnable lines.
- Reviews cover every line already in `player_lines`, including one that later
  becomes a heading when the catalog gains a longer line. Demo line 982 is such
  a heading and stays reviewable.

In the 2026-11-13 demo database, 1,889 lines can be learned and 830 are headings.
Learnable lines are 7 to 36 plies long, median 11.

**Why:** the derived rule stays correct when the catalog changes, without a
flag to keep in step.

**Rejected:** a stored `is_playable` flag. It is only needed for manual
exceptions and can drift from the tree.

**Trade-off accepted:** a player can no longer learn a short heading line,
such as the Najdorf with 6.Bg5, on its own before its subvariations.

### 9. Older databases are upgraded when the backend starts

`Store` rebuilds the two opening tables when it opens a database in an older
layout: the single-table catalog with an `opening_family` column, or the
two-table catalog with `side_in_games` and no `parent_line_id`. It keeps every
line ID and each surviving canonical family's ID, folds Accepted and Declined families into their gambit,
sets each family's side by decisions 1 and 3, and computes `parent_line_id`.
Practice history and progress are untouched. The rebuild runs in one
transaction and rolls back if a reference would break or a family's side
cannot be decided. It replaces the family-split migration added in `0d2dc08`.

Merged Accepted/Declined families do not keep separate IDs; a new canonical
family receives an ID. The older single-table catalog has no family IDs to
preserve. `Store._rebuild_catalog` implements these distinctions.

**Why:** the backend writes practice data into `backend/tempo_demo.sqlite`, so
contributors' local copies differ from the committed one. Upgrading at start-up
keeps their data.

**Rejected:** a one-off script that rewrites only the committed database and a
`Store` that refuses older layouts.

## Schema

```sql
CREATE TABLE opening_families (
    family_id   INTEGER PRIMARY KEY,
    name        TEXT NOT NULL UNIQUE,
    family_side TEXT NOT NULL CHECK (family_side IN ('white', 'black'))
);

CREATE TABLE opening_lines (
    line_id        INTEGER PRIMARY KEY,
    family_id      INTEGER NOT NULL REFERENCES opening_families,
    parent_line_id INTEGER REFERENCES opening_lines,
    name           TEXT NOT NULL,
    eco            TEXT NOT NULL,
    moves_uci      TEXT NOT NULL UNIQUE
);
CREATE INDEX opening_lines_family ON opening_lines (family_id);
CREATE INDEX opening_lines_parent ON opening_lines (parent_line_id);
```

`practice_events` and `player_lines` are unchanged.

## Implementation

| Path | What it does |
|---|---|
| `backend/store.py` | The schema; `family_name` and `family_side` hold decisions 1 and 3; `link_parents` computes decision 7; `LEARNABLE` and `is_learnable` hold decision 8; `Store._rebuild_catalog` is decision 9; `add_line` upserts on `moves_uci` (decision 6) |
| `backend/practice_controller.py`, `backend/ml_controller.py` | Refuse heading lines in Learning and in a new repertoire entry |
| `backend/demo.py` | Picks the first learnable line for the terminal demo |
| `backend/tempo_demo.sqlite` | Upgraded by decision 9: 82 families (43 white, 39 black), 2,719 lines, practice data unchanged |
| `frontend/src/lib/learning.ts` | `distinguishingMoves` labels same-name lines from the move where they first differ, for example "7…Be6 8.f3" (decision 5) |
| `frontend/src/lib/catalog.ts`, `frontend/src/components/LearnPage.tsx`, `frontend/src/components/FamilyPage.tsx`, `frontend/src/lib/practiceApi.ts` | Group the API catalog into families and show learnable lines with distinguishing moves; related lessons use shared opening plies |

The former `ml/ml_1000bots/openings/` workflow read separate CSV files and kept
`side_in_games` there. That folder was removed on 2026-11-14 and is retrievable
at `825e9d8`; it is not a current implementation path. The package generator's
`ml/tempo_ml/catalog.py` reads every database line and uses `family_side`; it
does not apply the app's leaf-only Learning restriction. Historical
game-evidence sources belong to the [opening library record](../opening-library/opening-library.md).
`backend/synthetic_clients.py` reads the new tables unchanged; with
`--one-line-per-family` it now draws from 82 families instead of 91.
`backend/synthetic_reviews.csv` was not regenerated.

## Evidence

Catalog counts before the change were measured on 2026-11-13 with read-only
Python 3.13 `sqlite3` queries against `backend/tempo_demo.sqlite` at commit
`0d2dc08` (sha256
`7b13a2d26a6116fea343bc047afc6b8390f09738d6ea3b7bb8b497ea63421db6`).
A line's parent is found by trying each shorter prefix of its `moves_uci`,
longest first, against the move sequences of its family. Family merges
strip a trailing " Accepted" or " Declined" from the family name. These are
counts over catalog data, not performance measurements.

Implementation checks, 2026-11-13, Python 3.13.5 with fsrs installed from
`backend/requirements.txt`, on copies of each database:

- Start-up upgrade of three layouts: the database at `0d2dc08`, the
  single-table catalog at `5cbe0a6` and the uncleaned single-table catalog at
  `4ef8d43` (3,865 lines). In each, every `line_id` kept its moves, practice
  events and progress rows kept their counts, the foreign-key check was clean, no family named Defense is White, no Accepted or
  Declined family remains, every parent is a same-family prefix, and a second
  start changed nothing.
- `backend/tempo_demo.sqlite` after the upgrade: sha256
  `5eb848f110d5f3634344b854038a4482a16c7d2ecc7da782b01c2b326188eaa0`; all
  79 surviving families kept their IDs, and Queen's Gambit, King's Gambit and
  Danish Gambit were created as families 94, 93 and 92.
- Controller flow: Learning line 1591 (a heading) is refused; line 1598 (Poisoned
  Pawn Accepted) is learned as Both and joins the repertoire; demo line 982, a
  heading already in a repertoire, is still suggested for review.
- `add_line`: re-adding line 1570's moves keeps `line_id` 1570 and updates its
  name; a line extending 1598 gets parent 1598 and makes 1598 a heading; a new
  family without a side is refused; a "Queen's Gambit Accepted" line lands in
  Queen's Gambit.
- HTTP API through `backend.web.Handler`: `/api/catalog` returns 2,719 lines,
  1,889 learnable, with `family_side`, `parent_line_id` and `learnable`;
  `/api/learning` answers 400 for line 1591 and starts line 1598.
- Terminal demo `python -m backend.demo` completes for White, Black and Both.
- Frontend, with Node.js 26.13.1 and npm 11.20.0: `npm ci` reported 0
  vulnerabilities; `npm test` passed 4 tests, including a new one for
  `distinguishingMoves`; `npm run build` passed the TypeScript check and the
  Vite 8.3.8 production build. With the backend and `npm run dev` running, the
  Learning page listed 1,889 lines, a search for "Najdorf Variation" showed 21
  lines with the four English Attack cards labelled "7…Be6 8.f3", "7…Be7 8.f3",
  "7…Be6 8.h3" and "7…Be7 8.h3", and the browser console showed no errors.
  Node.js 26 is newer than the Node 22 line the project context records.

### Read-only seed verification on 2026-11-15
A read-only SQLite query in the documentation environment confirmed 2,719
lines, 82 families (43 White, 39 Black), 1,889 learnable terminal variations,
and a minimum of four White moves. The connection used `mode=ro`; no startup
migration or practice session ran. The source remains `backend/tempo_demo.sqlite`.

Input identity: `5d6b81c:backend/tempo_demo.sqlite`, Git blob
`f955e4d5a141d8ff9d34fa66831a8f57c4d39613`, SHA-256
`5eb848f110d5f3634344b854038a4482a16c7d2ecc7da782b01c2b326188eaa0`.
Reproduce with the documentation interpreter from the project root:

```python
import sqlite3
db = sqlite3.connect('file:backend/tempo_demo.sqlite?mode=ro', uri=True)
lines = db.execute('SELECT moves_uci FROM opening_lines').fetchall()
print(len(lines))
print(db.execute('SELECT COUNT(*) FROM opening_families').fetchone()[0])
print(db.execute('SELECT family_side, COUNT(*) FROM opening_families GROUP BY family_side').fetchall())
print(min((len(row[0].split()) + 1) // 2 for row in lines))
print(db.execute('SELECT COUNT(*) FROM opening_lines o WHERE NOT EXISTS '
                 '(SELECT 1 FROM opening_lines p WHERE p.parent_line_id=o.line_id)').fetchone()[0])
db.close()
```

## Open questions

- The team has to confirm the catalog choices other than the same-family
  parent-link rule and startup migration, which the worklog records as settled.
  The [opening library open questions](../opening-library/opening-library.md#open-questions)
  include confirmation of side labels.
