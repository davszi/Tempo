# Catalog and data

## Scope and ownership

This topic owns the current opening catalog, its four-table SQLite storage
contract, line identity, family/parent/learnability decisions and startup
migration. [Historical provenance](provenance.md) retains the retired library
classifier, original input identities and game evidence; it is supporting
evidence within this topic, not a separate current subsystem.

[App & Practice](../app-practice/app-practice.md) owns the HTTP/UI contract and
practice lifecycle. [Architecture](../system-architecture/system-architecture.md)
owns runtime coordination; [Synthetic Players](../synthetic-clients/record.md)
owns simulated consumers. Catalog content is shared; per-player repertoire
and practice events remain separate. No current reproducible upstream-import
command is implemented in this checkout.

## Status

Implemented in the backend and frontend Learning flow; see
[implementation](#implementation). The catalog review was recorded on
2026-11-13. Same-family parent links and startup migration were settled with
the user, as recorded in [the worklog](../../worklog.md); the other catalog
choices still await team confirmation. See [open questions](#open-questions).
The current `ml/tempo_ml/catalog.py` reads this SQLite catalog; historical
opening-building scripts and their CSV workflow are described in
[opening library](provenance.md).

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
`ml/ml_1000bots/openings/side_evidence.py` (removed 2026-11-14 at `ea3d01d`; pre-removal source at `825e9d8`) copied onto every line of the
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

## opening_families (3 fields)

| Field | What it stores |
|---|---|
| `family_id` | Unique family ID. Primary key. |
| `name` | Unique family name, such as Sicilian Defense. Accepted and Declined lines belong to their gambit's family, such as Queen's Gambit. |
| `family_side` | Side the family belongs to: `white` or `black`. Required. |

## opening_lines (6 fields)

One row per opening line. Each line contains moves for both colors.

| Field | What it stores |
|---|---|
| `line_id` | Integer primary key. Current upserts and recognized migrations preserve existing line IDs. |
| `family_id` | Reference to `opening_families.family_id`. One family can have many lines. A line's side is its family's side. |
| `parent_line_id` | Reference to `opening_lines.line_id`: the longest other line of the same family whose moves start this line. Empty when there is none. |
| `name` | Full name of the opening line. Several lines can share a name. |
| `eco` | Lichess opening classification code. Multiple lines can share a code. |
| `moves_uci` | Unique ordered move sequence for White and Black in UCI notation. The line's permanent identity. |

A line can be learned only when no other line names it as `parent_line_id`. This is derived, not stored; `LEARNABLE` in `backend/store.py` holds the condition. Learning a line that other lines extend is refused, and only learnable lines can join a repertoire. A line already in a player's repertoire stays reviewable if the catalog later gains a longer line.

`Store.add_line` takes moves in UCI; convert PGN first. It inserts a line or, when the moves already exist, updates that line's family, name and ECO code and keeps its `line_id`. A new family needs a side. After every change it recomputes `parent_line_id` for the catalog. The family side is separate from the side selected for a practice session.

Startup migration is specified under [decision 9](#9-older-databases-are-upgraded-when-the-backend-starts).

## practice_events (12 fields)

One row per suggestion, move attempt, or completed session.

| Field | What it stores |
|---|---|
| `event_id` | Unique event ID. Primary key. |
| `player_id` | Player the event belongs to. |
| `line_id` | Reference to opening_lines.line_id. |
| `session_id` | Groups events from the same session. Can be empty for a suggestion. |
| `event_type` | line_suggested, move_attempted, or session_completed. |
| `mode` | learning or repeating. |
| `side` | Perspective used by the session: white, black, or both. Empty for planner suggestion events. The browser currently selects the family side automatically; the backend/demo also support a chosen side. |
| `occurred_at` | UTC timestamp with microsecond precision, serialized as ISO 8601 text. |
| `move_index` | Zero-based position of the expected move in the full line. Filled for move attempts. |
| `is_correct` | Whether the move attempt matched the expected move. Filled for move attempts. |
| `response_time_ms` | Server monotonic time since the side was selected or the previous attempt completed, rounded to nonnegative milliseconds. Includes request/UI waiting time; filled for move attempts. |
| `fsrs_rating` | Again, Hard, Good, or Easy for a completed Repeating session, including one closed early after a mistake. Empty for Learning completion. |

## player_lines (6 fields)

One row per player and opening line. The primary key is (player_id, line_id).

| Field | What it stores |
|---|---|
| `player_id` | Player who owns this progress record. |
| `line_id` | Reference to opening_lines.line_id. |
| `learned_at` | When the player first completed Learning for this line as White, Black, or Both. |
| `last_reviewed_at` | When the player last completed a review of the line or closed one early after a mistake. |
| `next_review_at` | When the line is due for review again. |
| `fsrs_state` | Current FSRS state used to update the review schedule. |


### Declared types and required values

Verified against `CATALOG_SCHEMA` and `PRACTICE_SCHEMA` in `backend/store.py`
at `788e060`; this table retains the exact declared storage types and
nullability that the former catalog DDL specified. Integer primary keys are
SQLite rowid keys and may be generated when omitted. No `AUTOINCREMENT` or
cross-deletion never-reuse promise is declared; the current upsert/migration
operations preserve existing line IDs.

| Column | SQLite type | Required value |
|---|---|---|
| `opening_families.family_id` | `INTEGER` | generated integer primary key |
| `opening_families.name` | `TEXT` | required (NOT NULL) |
| `opening_families.family_side` | `TEXT` | required (NOT NULL) |
| `opening_lines.line_id` | `INTEGER` | generated integer primary key |
| `opening_lines.family_id` | `INTEGER` | required (NOT NULL) |
| `opening_lines.parent_line_id` | `INTEGER` | nullable |
| `opening_lines.name` | `TEXT` | required (NOT NULL) |
| `opening_lines.eco` | `TEXT` | required (NOT NULL) |
| `opening_lines.moves_uci` | `TEXT` | required (NOT NULL) |
| `practice_events.event_id` | `INTEGER` | generated integer primary key |
| `practice_events.player_id` | `TEXT` | required (NOT NULL) |
| `practice_events.line_id` | `INTEGER` | required (NOT NULL) |
| `practice_events.session_id` | `TEXT` | nullable |
| `practice_events.event_type` | `TEXT` | required (NOT NULL) |
| `practice_events.mode` | `TEXT` | required (NOT NULL) |
| `practice_events.side` | `TEXT` | nullable |
| `practice_events.occurred_at` | `TEXT` | required (NOT NULL) |
| `practice_events.move_index` | `INTEGER` | nullable |
| `practice_events.is_correct` | `INTEGER` | nullable |
| `practice_events.response_time_ms` | `INTEGER` | nullable |
| `practice_events.fsrs_rating` | `TEXT` | nullable |
| `player_lines.player_id` | `TEXT` | required (NOT NULL) |
| `player_lines.line_id` | `INTEGER` | required (NOT NULL) |
| `player_lines.learned_at` | `TEXT` | required (NOT NULL) |
| `player_lines.last_reviewed_at` | `TEXT` | nullable |
| `player_lines.next_review_at` | `TEXT` | required (NOT NULL) |
| `player_lines.fsrs_state` | `TEXT` | required (NOT NULL) |

The composite `player_lines` primary key is `(player_id, line_id)`; both
columns are explicitly required. Named uniqueness, foreign keys and check
constraints are described under Storage operations and constraints.

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
game-evidence sources belong to the [opening library record](provenance.md).
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
  The [opening library open questions](provenance.md#open-questions)
  include confirmation of side labels.

## Catalog and data overview sources

The requested `opening-catalog.html` combines a human overview of catalog
provenance, the current line tree and the four-table practice-data model.
This record owns catalog rationale, field mappings, storage operations and
migration. `provenance.md` retains the historical classifier and side evidence
inside the same topic. That is retired tooling, not a current import command. Plans,
checks and full evidence remain in Reference rather than separate main pages.

The source-authored HTML figures in `index.md` are their own generators. The
relationship diagram uses the field mapping retained here and `backend/store.py` at
`dab04ac`; its arrows mean foreign-key references, with the composite
`player_lines` key shown explicitly. There is no players table. The runtime
practice-data sequence uses the retained schema mapping and controller sources at the
same pin.

A read-only SQLite query on 2026-11-15 supplied the illustrated tree example.
The input SHA-256 is
`5eb848f110d5f3634344b854038a4482a16c7d2ecc7da782b01c2b326188eaa0`,
the same seed identified above; app source pin is `dab04ac`. The documentation
interpreter executed this query without opening the backend or migrating data:

```python
import sqlite3
con = sqlite3.connect('file:backend/tempo_demo.sqlite?mode=ro', uri=True)
rows = con.execute(
    'SELECT o.line_id, o.parent_line_id, o.name, o.moves_uci, '
    'NOT EXISTS (SELECT 1 FROM opening_lines c '
    'WHERE c.parent_line_id=o.line_id) AS learnable '
    'FROM opening_lines o WHERE o.line_id=2642 OR o.parent_line_id=2642 '
    'ORDER BY o.line_id').fetchall()
print(rows)
con.close()
```

Verified output: 2642, Ruy Lopez: Steinitz Defense, is a root heading. Its four
children are learnable leaves: 2643 Center Gambit, 2644 Nimzowitsch Attack,
2645 Semi-Duras Variation, and 2683 Berlin Defense, Tarrasch Trap. Each shares
2642's prefix `e2e4 e7e5 g1f3 b8c6 f1b5 d7d6 d2d4`. Names do not define
parentage: even the Tarrasch Trap's stored name differs, while its moves have
this same-family prefix. No new chess classification is inferred.

Numeric ledger: 2,719 lines, 82 families and 1,889 learnable leaves reuse the
read-only seed verification above; 830 headings is 2,719 minus 1,889,
already recorded in decision 8. Four tables and their primary/foreign keys
come from database-schema. Example line IDs and the four-child claim come
from the exact query above. These are seed facts, not counts guaranteed for
every user's modified database. No experimental result is changed.

## Storage operations and constraints

Source inspection at `788e060` on 2026-11-15 covers all of `backend/store.py`.
These are implementation facts, not new runtime or migration test results.

- `Store.transaction` opens a short-lived SQLite connection per operation,
  sets row access to `sqlite3.Row` and enables foreign keys by default. Writes
  explicitly use `BEGIN IMMEDIATE`; the connection context commits on success
  or rolls back on an exception, and always closes. No WAL, backup policy,
  retention policy or application-level busy retry is configured here.
- Construction creates missing tables. Recognized legacy layouts trigger the
  transactional rebuild described in decision 9. This is a specific layout
  detector, not a general schema-version migration framework. Migration turns
  foreign-key enforcement off on that connection, then checks all references
  before committing. `run_statements` avoids `executescript`'s implicit commit.
- `Store.add_line` normalizes whitespace and rejects empty moves. It accepts
  UCI text without validating chess legality. It folds family suffixes, creates
  a missing family using `family_side`, upserts on the unique move sequence,
  and recomputes all parent links inside the write transaction. For an existing
  family, a supplied side does not update the stored family side. This API
  offers no deletion, family relabel or PGN-import operation.
- `family_side` first uses the Queen's Gambit, Benko Gambit and Four Knights
  overrides, then the Defense/Defence name rule, then an unambiguous supplied
  existing side. Otherwise it raises. These implemented decisions retain the
  team's confirmation status under Open questions.
- `list_lines` returns catalog metadata and a derived `learnable` boolean,
  ordered by family name, line name and line ID. `learning_catalog(player_id)`
  also returns moves and whether that player's repertoire contains the line;
  it returns headings too, so the consumer still filters learnability.
- `repertoire_rows` selects that player's progress joined to catalog details,
  ordered by due date, first learned date and line ID. It attaches repeating
  completion history in insertion/event-ID order. Recall and stability are
  derived later by the runtime, not stored as extra columns. `add_event`
  serializes supplied timestamps to UTC ISO text with microseconds.
- Family names and ordered move strings are unique. Catalog name and ECO are
  required, with no uniqueness constraint on either. There is no players or
  accounts table: `player_id` is required text, and `(player_id, line_id)` is
  the progress primary key. The HTTP layer's UUID check is an application
  boundary, not a database identity/authentication constraint.
- Table checks restrict family side, event type, mode, optional session side,
  correctness, nonnegative response time and optional FSRS grade. Foreign keys
  connect families, lines, parent lines, events and progress. They do not prove
  that a parent is a shorter same-family prefix; `link_parents` establishes
  that property. The database does not validate UCI legality, timestamp format,
  FSRS JSON validity or per-event conditional field requirements.
- Named indexes are `opening_lines_family`, `opening_lines_parent`,
  `practice_events_player` on `(player_id, event_id)` and `player_lines_due`
  on `(player_id, next_review_at)`, in addition to uniqueness/primary-key
  indexes. Suggestion events and completed reviews have different meanings;
  current chosen-line reviews omit suggestions. Browser-local progress and
  active process sessions live outside these tables.

## Code coverage and verification limits

| Reviewed source or input | Owning explanation | Gap filled in this pass |
|---|---|---|
| `backend/store.py`: schemas and indexes | Schema; Storage operations and constraints | Database-enforced checks versus controller assumptions; indexes and missing identity table |
| `timestamp`, `run_statements`, `Store.transaction` | Storage operations and constraints | UTC serialization, short connections, write locking, rollback and missing operational policies |
| `family_name`, `family_side`, `link_parents`, `is_learnable` | Decisions 1, 3, 7, 8; Storage operations | Side precedence, same-family prefix mechanism and leaf derivation |
| `Store.__init__`, `_rebuild_catalog` | Decision 9; Evidence | Exact layout detection and retained historical migration scope |
| `add_line`, `list_lines`, `learning_catalog` | Decisions 5/6; Storage operations | Whitespace/upsert semantics, existing-family side behavior, headings in API data |
| `repertoire_rows`, `add_event` | Schema; Storage operations | Ordering, completion history and derived runtime fields |
| `backend/tempo_demo.sqlite` | Read-only seed verification; query below | Current fields, indexes, counts and foreign-key closure checked without mutation |
| Removed `ml/ml_1000bots/openings/` | Historical provenance | Historical classifier/side evidence separated from current import capability |

A fresh read-only check used Python 3.12.14 `sqlite3` in `.build/docs-env`.
It confirmed 82 families, 2,719 lines, 1,889 leaves, the four documented table
layouts and named indexes, and no `PRAGMA foreign_key_check` rows. SHA-256
before and after remained
`5eb848f110d5f3634344b854038a4482a16c7d2ecc7da782b01c2b326188eaa0`.
Reproduce from the repository root with the documentation interpreter:

```python
from pathlib import Path
import sqlite3
p = Path('backend/tempo_demo.sqlite').resolve()
with sqlite3.connect(p.as_uri() + '?mode=ro', uri=True) as db:
    for table in ('opening_families', 'opening_lines', 'practice_events', 'player_lines'):
        print(table, list(db.execute('PRAGMA table_info(' + table + ')')))
        print(list(db.execute('PRAGMA index_list(' + table + ')')))
    print(list(db.execute('PRAGMA foreign_key_check')))
    print(db.execute('SELECT COUNT(*) FROM opening_families').fetchone())
    print(db.execute('SELECT COUNT(*) FROM opening_lines').fetchone())
    print(db.execute('SELECT COUNT(*) FROM opening_lines o WHERE NOT EXISTS '
                     '(SELECT 1 FROM opening_lines c WHERE c.parent_line_id=o.line_id)').fetchone())
```

The check did not call `Store`, open a write connection, migrate a database,
exercise lock contention or run an app session. The older migration checks
above retain their original source/environment. A complete current upstream
rebuild and a database operational/recovery policy remain product work;
this audit supplies no invented import or backup command.

## Retired duplicate schema page

The actual topic consolidation replaces the separate database-schema record
and hand-maintained `database-schema.html` with this topic's complete field
mapping and requested `opening-catalog.html` explanation. The former standalone
page contained the same four-table lookup and practice notes, no separate
interactive or measured evidence. Repository searches found no runtime caller.
Its historical bytes remain at
[788e060:docs/topics/database-schema/database-schema.html](https://github.com/davszi/Tempo/blob/788e06039dd2869b23261dd80ea8fc49367ab33c/docs/topics/database-schema/database-schema.html).
The current supported topic URL `opening-catalog.html` is unchanged; retired
source/Reference paths are replaced by the current topic routes in live docs.
