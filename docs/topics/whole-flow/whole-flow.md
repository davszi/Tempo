# TEMPO end-to-end flow

This walkthrough connects the [system architecture](../system-architecture/system-architecture.md), [database schema](../database-schema/database-schema.md), and [review dataset](../review-dataset/record.md) to the local presentation demo.

## 1. Prepare the opening catalog and weights

The demo catalog holds 2,719 Lichess opening lines in 82 families. Moves are stored in UCI in `opening_lines` with names and ECO codes; `opening_families` holds each family's side. Lines that other lines extend are headings and cannot be learned; see [opening catalog structure](../opening-catalog/opening-catalog.md). The local demo uses `backend/tempo_demo.sqlite` and loads the supplied 21 FSRS parameters from `backend/fitted_global.csv` at startup.

## 2. Learn, repeat, and schedule

1. In Learning, the player chooses a line and a side. The practice controller loads the line and provides hints. Each attempted move is saved to `practice_events`. First completion adds the line to `player_lines` and makes its first review due immediately.
2. In Repeating, the ML controller loads the player's repertoire. The ML engine selects the most overdue line. The player then chooses White, Black, or Both. Repeating has no move hints. A wrong move leaves the position unchanged for a retry.
3. On completion, the ML controller sends the recorded attempts and saved card state to the ML engine. The engine assigns `Again`, `Hard`, `Good`, or `Easy`, then calls Py-FSRS with the fitted weights to update stability and calculate the next due date.
4. TEMPO commits the final attempt, completed review, and updated `player_lines` schedule in one SQLite transaction. A learning step may schedule the next review in minutes even when estimated stability is measured in days.

## 3. Run and inspect the demo

From the repository root in PowerShell:

```powershell
.\backend\run-demo.cmd
.\backend\run-demo.cmd --side black --grade Again
```

The first command simulates a clean Both-side review. The second simulates a wrong move and retry. Both print a fresh player ID, grade, stability, and next review time in UTC. Open `backend/tempo_demo.sqlite` in DB Browser for SQLite and filter `practice_events` and `player_lines` by that player ID. The terminal demo runs independently of the browser frontend.

## 4. Generate offline training data

The [synthetic clients](../synthetic-clients/record.md) use the opening catalog to simulate recall and timing. The demo dataset in `backend/synthetic_reviews.csv` contains 50,400 sessions from 30 agents on 140 representative opening lines. The generator reads the catalog without adding synthetic practice events to SQLite. The supplied fitted weights came from a separate training run. The local app consumes the weights CSV, while model fitting runs offline.
