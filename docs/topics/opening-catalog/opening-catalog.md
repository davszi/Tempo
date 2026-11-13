# Opening catalog structure

## Scope

This record owns the accepted target structure of TEMPO's opening catalog in
the backend database: how opening families and lines are stored, which side
each family belongs to, how lines relate to each other, and which lines a
player can learn. The schema as implemented today is described in
[TEMPO database schema](../database-schema/database-schema.md). Where the
library's lines come from and how their sides were first classified is in
[opening library](../opening-library/opening-library.md).

## Status

Accepted future specification, not implemented. The decisions below were made
in a catalog design review on 2026-11-13. The team has not confirmed them yet;
see [open questions](#open-questions). Until they land, the
[database schema record](../database-schema/database-schema.md) describes the
running system.

## Decisions

### 1. A family belongs to White or Black

`opening_families.family_side` holds only `white` or `black` and is required.
`both` and empty values are removed.

- A family named "Defense" is a Black opening.
- Four Knights Game, the one family labelled `both` today (48 lines), becomes
  `white`.
- A player can still practise any line from White, Black or both sides. That
  choice belongs to the session (`practice_events.side`), not to the catalog.
  Practising the other side is a learning aid for knowing the replies; it does
  not change which side a line belongs to.

**Why:** the family side states what the opening is. The Queen's Gambit is a
White opening even when a player drills Black's replies.

### 2. Remove `opening_lines.side_in_games`

A line's side is its family's side. The per-line game-evidence column is
dropped from the schema, the demo database, `Store.add_line` and the catalog
queries.

**Why:** the column is a per-family measurement from
`ml/ml_1000bots/openings/side_evidence.py` copied onto every line of the
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

`opening_lines` gains a nullable `parent_line_id`: the longest other catalog
line whose moves are a prefix of this line's moves. It is computed once when
the catalog is built. Families stay flat; the tree runs inside them.

In the demo database, 1,820 of 2,719 lines have a parent across the whole
catalog. Restricted to the same family after the merges of decision 3, 1,774
lines have a parent and 945 are roots.

**Why:** the tree shows how lines branch, so lines with the same name sit at
different points and can be learned in order. Scheduling and progress do not
change.

**Rejected for now:** a full move tree that stores each position once (7,843
distinct move prefixes against 32,511 stored moves). It would change the
scheduler and practice logic and is only worth it for per-move learning.

### 8. Only subvariations can be learned

A line can be learned only when no other line has it as `parent_line_id`. The
shorter lines become headings in the tree; their moves are practised as the
start of every subvariation below them. Learnability is derived from the tree
and not stored:

```sql
NOT EXISTS (SELECT 1 FROM opening_lines c WHERE c.parent_line_id = o.line_id)
```

- `Store.learning_catalog` returns headings for the tree but marks them as not
  learnable.
- `MLController` refuses to add a heading line to a repertoire.
- Reviews cover every line already in `player_lines`, including one that later
  becomes a heading when the catalog gains a longer line. Demo line 982 is such
  a heading today and stays reviewable.

With whole-catalog parents, 1,873 lines can be learned and 846 are headings;
with same-family parents after the merges, 1,889 and 830. Learnable lines are
7 to 36 plies long, median 12.

**Why:** the derived rule stays correct when the catalog changes, without a
flag to keep in step.

**Rejected:** a stored `is_playable` flag. It is only needed for manual
exceptions and can drift from the tree.

**Trade-off accepted:** a player can no longer learn a short heading line,
such as the Najdorf with 6.Bg5, on its own before its subvariations.

## Target schema

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

## Affected code and data

Found by searching the repository at commit `0d2dc08`:

| Path | Change |
|---|---|
| `backend/store.py` | Schema, the start-up catalog migration, `add_line` upsert, `list_lines`, `learning_catalog` |
| `backend/ml_controller.py` | Refuse heading lines when adding to a repertoire |
| `backend/synthetic_clients.py` | Reads the catalog; check after the schema change |
| `backend/tempo_demo.sqlite` | Family sides, merged families, dropped column, `parent_line_id` |
| `ml/ml_1000bots/openings/classify.py`, `side_evidence.py` | Side rules and the `side_in_games` output column |
| `ml/ml_300bots/ml_engine/src/tempo_ml/openings.py` | Its side filter reads `side_in_games` |
| `frontend/` | Distinguishing move for same-name lines; tree and heading display |
| [database schema](../database-schema/database-schema.md), [opening library](../opening-library/opening-library.md) | Updated when the change lands |

## Evidence

All counts in this record were measured on 2026-11-13 with read-only Python
3.13 `sqlite3` queries against `backend/tempo_demo.sqlite` at commit
`0d2dc08` (sha256
`7b13a2d26a6116fea343bc047afc6b8390f09738d6ea3b7bb8b497ea63421db6`).
A line's parent is found by trying each shorter prefix of its `moves_uci`,
longest first, against the set of catalog move sequences. Family merges
strip a trailing " Accepted" or " Declined" from the family name. These are
counts over catalog data, not performance measurements.

## Open questions

- The team has to confirm these decisions, as the
  [opening library open questions](../opening-library/opening-library.md#open-questions)
  ask for the side labels.
- Whether `parent_line_id` may point into another family. After the merges,
  55 lines have their longest prefix in a different family, for example
  Pterodactyl Defense lines extending Modern Defense. Keeping links inside a
  family changes the counts in decisions 7 and 8.
- Whether the backend keeps a start-up migration for older databases or the
  demo database is rebuilt. The current migration in `backend/store.py` was
  added by another contributor; changing it follows the kit's
  refactoring-over-compatibility rule in `.docs-kit/rules/engineering/code.md`.
