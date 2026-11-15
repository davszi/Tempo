# TEMPO end-to-end flow

This walkthrough connects the [system architecture](../system-architecture/system-architecture.md), [database schema](../database-schema/database-schema.md), [frontend application](../frontend/frontend.md) and [review dataset](../review-dataset/record.md). It describes source inspected at `5d6b81c` on 2026-11-15; no runtime checks were rerun for this documentation pass.

## 1. Prepare the opening catalog and weights

The 2026-11-13 catalog check recorded 2,719 Lichess opening lines in 82 families, with 1,889 learnable leaves and 830 headings. These are dated seed-catalog counts, not a promise about every locally modified database. [Opening catalog evidence](../opening-catalog/opening-catalog.md#evidence) records the source and checks. `opening_lines` stores UCI moves, names, ECO codes and same-family parent links; `opening_families` stores family sides. A heading cannot start Learning, while a line already in a repertoire remains reviewable if it later becomes a heading.

The local web server and terminal launcher use `backend/tempo_demo.sqlite` and load 21 supplied parameters from `backend/fitted_global.csv`. The Python web server serves HTTP on loopback; Vite proxies API requests during frontend development. Setup and commands are in [project context](../../PROJECT_CONTEXT.md#build-and-review). Hosted HTTPS remains a deployment proposal.

## 2. Learn, repeat, and schedule

1. The browser fetches the catalog and repertoire for its locally stored player UUID. In Learning the player chooses a line; the browser supplies the family side automatically. Backend/demo callers can also choose White, Black or Both. The controller provides Learning hints, checks each move against the prescribed UCI move and saves attempts in `practice_events`. Wrong moves leave the position unchanged.
2. First Learning completion adds the line to `player_lines` with a card due immediately. A later Learning completion preserves existing progress and schedule. Unfinished browser lesson positions are stored locally and can open a new session through `resume_at`; the active backend session itself is not persisted.
3. Normal Start review loads the player's repertoire and selects the earliest due line, breaking ties by first learned date then line ID. It records `line_suggested`, opens the line and awaits a side; the browser automatically supplies the family side. Empty repertoire and nothing due are explicit response states. The selector does not consult past suggestions or the full event history.
4. The merged browser also allows chosen-line reviews, including early reviews, and reveals the expected move after the first mistake. These conflict with the settled planner-only/no-hints Repeating contract. [The unresolved choice](../frontend/frontend.md#unresolved-repeating-behavior) owns the discrepancy; this walkthrough does not approve it. In both cases wrong moves leave the position unchanged. Direct review does not record a planner suggestion.
5. On completion, the ML controller sends saved card state and recorded session attempts to the engine. Any wrong attempt gives Again. Clean reviews use baseline-adjusted mean response time per distinct move: under 500 ms Easy; 500 through 1,800 ms Good; slower Hard. The web baseline is zero. Py-FSRS updates the card and next due date with the supplied weights.
6. The final attempt, completed review and updated schedule commit in one SQLite transaction. Choosing re-learning after review mistakes uses the early-close API to record Again and reschedule before Learning starts. Ordinary navigation away leaves no completion. An FSRS learning/relearning step may schedule a review in minutes even when stability is measured in days; scheduled due time is not an exact guarantee of a target-recall crossing.

The dashboard, review queue and repertoire display saved schedules and the last fetched recall estimates. UTC timestamps are shown in local browser time. The 30-day timeline groups overdue reviews into today; it is a view of current due dates, not a forecast of later reviews after those sessions occur.

## 3. Run and inspect the demo

From the repository root in PowerShell:

```powershell
.\backend\run-demo.cmd
.\backend\run-demo.cmd --side black --grade Again
```

The first command simulates a clean Both-side review graded Good. The second simulates a wrong move and retry graded Again. Both print a fresh player ID, grade, stability and next review time in UTC. They write into the selected demo SQLite file. In DB Browser for SQLite, filter `practice_events` and `player_lines` by the printed player ID. The terminal demo runs independently of the browser frontend and uses simulated response timing; it does not measure human recall or browser interaction latency.

## 4. Generate offline training data

The presentation generator `backend/synthetic_clients.py` reads the catalog read-only and writes CSV rather than inserting synthetic practice events into SQLite. The supplied `backend/synthetic_reviews.csv` is a historical export recorded as 50,400 sessions from 30 agents on 140 representative lines. It was not regenerated after the catalog was cleaned and merged; generating one line per family from the later catalog uses its new family count. This CSV is separate from the run that produced the app's supplied weights.

The maintained generation, training and evaluation pipeline lives in `ml/tempo_ml/`, with configurations in `ml/configs/` and dated results in `ml/experiments/`. [FSRS training](../fsrs-training/fsrs-training.md) owns methods, results, weight provenance and limitations; the package guide owns its commands. The app consumes a configured weights CSV. It does not launch offline fitting, import the newest experiment automatically, or fine-tune on the current player's live history.

## Slide design review

The existing faces `whole-flow#catalog`, `#learning-to-schedule` and `#present-and-inspect` remain in place. The
[2026-11-15 rendered review](../../worklog.md#2026-11-15-relocate-the-kit-audit) records their
title-first emphasis, broad empty bands and text-heavy layouts. Kit 5
asks for a real visual per face. Options: redraw the faces, remove
those with nothing visual to add, or explicitly retain them as a
temporary exception. Recommend a separate approved design pass.
Redrawing or removing these faces waits on that decision; passing lint
does not establish design conformance.
