# TEMPO database schema

TEMPO uses four SQLite tables for opening families, opening lines, practice history, and each player's repertoire and review schedule.

Opening lines are sourced from the [Lichess chess-openings dataset](https://huggingface.co/datasets/Lichess/chess-openings).

[Opening catalog structure](../opening-catalog/opening-catalog.md) owns why the opening tables have this shape: family sides, merged gambit families, the line tree and which lines can be learned.

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
| `line_id` | Unique opening line ID. Primary key. Never reassigned. |
| `family_id` | Reference to `opening_families.family_id`. One family can have many lines. A line's side is its family's side. |
| `parent_line_id` | Reference to `opening_lines.line_id`: the longest other line of the same family whose moves start this line. Empty when there is none. |
| `name` | Full name of the opening line. Several lines can share a name. |
| `eco` | Lichess opening classification code. Multiple lines can share a code. |
| `moves_uci` | Unique ordered move sequence for White and Black in UCI notation. The line's permanent identity. |

A line can be learned only when no other line names it as `parent_line_id`. This is derived, not stored; `LEARNABLE` in `backend/store.py` holds the condition. Learning a line that other lines extend is refused, and only learnable lines can join a repertoire. A line already in a player's repertoire stays reviewable if the catalog later gains a longer line.

`Store.add_line` takes moves in UCI; convert PGN first. It inserts a line or, when the moves already exist, updates that line's family, name and ECO code and keeps its `line_id`. A new family needs a side. After every change it recomputes `parent_line_id` for the catalog. The family side is separate from the side selected for a practice session.

When the backend opens a recognized older database layout, it rebuilds the two opening tables inside one transaction. It keeps every `line_id` and the IDs of surviving canonical families. Accepted and Declined families merge into their gambit and do not retain separate IDs; newly created canonical families receive IDs. The older single-table layout has no family IDs to preserve. The rebuild sets each family's side, drops `side_in_games` and computes `parent_line_id`. Practice history and progress are untouched. The transaction rolls back if any reference would break or a family's side cannot be decided. `Store._rebuild_catalog` in `backend/store.py` owns this behavior.

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

## Repertoire and reviews

- A player's repertoire contains their player_lines rows with learned_at set. Later Learning sessions preserve the first completion date.
- The normal review-start path records `line_suggested` when the planner selects a due line. The direct chosen-line review path does not record a suggestion. Both paths use the same practice-event and progress tables.
- The controller can open a planner-selected review before White, Black or Both is chosen. The current browser supplies the family side automatically. In Both, the player makes every move in one run; the full-line move_index identifies each attempted move's color.
- A completed review records one session completion in practice_events and updates last_reviewed_at, next_review_at, and fsrs_state once in player_lines.
- Closing a review through `abandon_review` requires a recorded mistake; it saves a `session_completed` event and updates the schedule with Again in one transaction. Ordinary navigation away from a session does not save completion. Active sessions and unfinished browser lesson positions are not SQLite tables; see [frontend persistence](../frontend/frontend.md#identity-and-persistence).
- `fsrs_state` is serialized Py-FSRS card JSON. The repertoire API derives stability, current recall and review history rather than storing additional columns. [Frontend HTTP interface](../frontend/frontend.md#http-interface) owns the response contract.

Chosen-line reviews and first-mistake hints are implemented deviations from the settled Repeating requirements, not accepted schema requirements; see [the unresolved choice](../frontend/frontend.md#unresolved-repeating-behavior).

## Verification scope

The 2026-11-15 documentation audit inspected `backend/store.py`, `backend/practice_controller.py`, `backend/ml_controller.py` and the browser callers at `5d6b81c`. It did not open or migrate a live database or rerun controller tests. Historical migration checks and catalog counts are retained in [opening catalog evidence](../opening-catalog/opening-catalog.md#evidence).
