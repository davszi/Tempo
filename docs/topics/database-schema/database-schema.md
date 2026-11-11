# TEMPO database schema

TEMPO uses three SQLite tables for opening lines, practice history, and each player's current repertoire and review schedule.

Opening lines are sourced from the [Lichess chess-openings dataset](https://huggingface.co/datasets/Lichess/chess-openings).

## opening_lines (7 fields)

One row per opening line. Each line contains moves for both colors.

| Field | What it stores |
|---|---|
| `line_id` | Unique opening line ID. Primary key. |
| `opening_family` | Opening group shown in the UI, such as Sicilian Defence. |
| `name` | Full name of the opening line. |
| `eco` | Lichess opening classification code. Multiple lines can share a code. |
| `moves_uci` | Full move sequence for White and Black in UCI notation. |
| `family_side` | Side traditionally associated with the opening family. White, Black, Both, or empty if unknown. |
| `side_in_games` | Side supported by observed Lichess games. White, Black, Both, or empty when evidence is unavailable. |

The catalog's family maps to opening_family. Convert pgn to moves_uci before inserting. The side labels describe catalog entries and are separate from the side selected for a practice session.

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
| `side` | Selected perspective for the session. Values are white, black, or both. Can be empty for a suggestion made before the player chooses. |
| `occurred_at` | When the event happened. |
| `move_index` | Position of the expected move in the full line. Filled for move attempts. |
| `is_correct` | Whether the move attempt matched the expected move. Filled for move attempts. |
| `response_time_ms` | Time taken to attempt the move in milliseconds. Filled for move attempts. |
| `fsrs_rating` | Again, Hard, Good, or Easy for a completed Repeating session. |

## player_lines (6 fields)

One row per player and opening line. The primary key is (player_id, line_id).

| Field | What it stores |
|---|---|
| `player_id` | Player who owns this progress record. |
| `line_id` | Reference to opening_lines.line_id. |
| `learned_at` | When the player first completed Learning for this line as White, Black, or Both. |
| `last_reviewed_at` | When the player last completed a review of the line. |
| `next_review_at` | When the line is due for review again. |
| `fsrs_state` | Current FSRS state used to update the review schedule. |

## Repertoire and reviews

- A player's repertoire contains their player_lines rows with learned_at set. Later Learning sessions preserve the first completion date.
- The planner opens a due line before the player selects White, Black, or Both. In Both, the player makes every move in one run. The full-line move_index identifies the color of each attempted move.
- A completed review records one session completion in practice_events and updates last_reviewed_at, next_review_at, and fsrs_state once in player_lines.
