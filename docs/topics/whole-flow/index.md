+++
title = "TEMPO End-to-End Flow"
slug = "whole-flow"
toc = []
components = ["toc", "nav", "filelinks"]
page_css = ["build-sheet.css"]
+++

# TEMPO End-to-End Flow

<section class="card" id="catalog">

<!-- slide -->
<p class="slide-eyebrow">Catalog and weights</p>
<p class="slide-title">The demo starts with a real opening catalog and fitted FSRS weights</p>
<div class="slide-main"><div class="slide-row">
<div class="slide-tile is-term"><h4>Opening catalog</h4><p>2,719 lines across 82 families</p></div>
<div class="slide-tile"><h4>SQLite</h4><p>Stores the move sequences and player progress</p></div>
<div class="slide-tile"><h4>FSRS configuration</h4><p>21 supplied weights loaded from CSV</p></div>
</div></div>
<p class="slide-scope">Catalog counts recorded 2026-11-13 · supplied demo weights</p>
<!-- /slide -->

## Prepare the catalog and weights

The 2026-11-13 seed-catalog check recorded 2,719 Lichess opening lines across 82 families: 1,889 learnable leaves and 830 headings. These dated counts do not describe every locally modified database. During import, PGN sequences were converted to UCI and stored with names, ECO codes and side classifications. The local web server and terminal demo load 21 supplied weights from `backend/fitted_global.csv` at startup. See the [catalog and weights record](../topics/whole-flow/whole-flow.md#1-prepare-the-opening-catalog-and-weights) for scope and evidence.

The React browser app connects to the local Python HTTP server through Vite's API proxy or the backend's built-frontend serving path. Hosted HTTPS remains proposed. See the [system architecture](system-architecture.html#components) for the component diagram and boundaries.

</section>

<section class="card" id="learning-to-schedule">

<!-- slide -->
<p class="slide-eyebrow">Practice flow</p>
<p class="slide-title">Learning adds a line, and Repeating updates its schedule</p>
<div class="slide-main"><div class="slide-row">
<div class="slide-tile is-term"><h4>Learn</h4><p>Choose a line and practise with hints.</p></div>
<div class="slide-tile"><h4>Repeat</h4><p>Normal Start review opens a due line for recall.</p></div>
<div class="slide-tile"><h4>Schedule</h4><p>Grade the review and save the next due date.</p></div>
</div></div>
<p class="slide-scope">Current app flow · direct-line reviews and mistake hints conflict with the settled contract</p>
<!-- /slide -->

## From Learning to the next review

1. The **practice controller** loads the chosen learnable line, provides Learning hints and records attempts in SQLite. The browser supplies the opening family's side; backend/demo callers can choose White, Black or Both. First Learning completion adds a card due immediately; later Learning preserves its schedule.
2. Normal Start review asks the **ML controller** and **ML engine** for the earliest due repertoire line, breaking ties by learned date and line ID. It records a suggestion. The browser supplies the family side. The selector does not consult prior suggestions or the full event history.
3. Current browser routes also allow direct-line reviews, including early reviews, and show an expected-move hint after the first mistake. These conflict with the settled planner-only/no-hints contract. The [unresolved Repeating behavior](../topics/frontend/frontend.md#unresolved-repeating-behavior) owns the decision. Direct review records no planner suggestion. Wrong moves leave the position unchanged for retry.
4. The **ML engine** gives Again after any wrong attempt. For clean reviews, mean server-recorded response time per distinct move minus baseline gives Easy below 500 ms, Good from 500 through 1,800 ms and Hard above 1,800 ms. The web baseline is zero; timing includes waiting and idle time rather than isolating thought. Py-FSRS uses the grade, saved card and supplied weights to update stability and due date.
5. The final attempt, completion and schedule update commit together. Early close after mistakes records Again before re-learning. Ordinary navigation away does not complete a review. See the [complete flow record](../topics/whole-flow/whole-flow.md#2-learn-repeat-and-schedule) for persistence and timing limits.

The dashboard, queue and repertoire show saved schedules and the last fetched recall estimates. UTC timestamps display in local browser time. The 30-day timeline groups overdue work into today; it shows current due dates rather than predicting later reviews after practice.

| SQLite table | What to inspect |
|---|---|
| `opening_lines` | Catalog names, move sequences, and each line's parent in the line tree. Family sides are in `opening_families`. |
| `practice_events` | Move attempts, suggestions, and the completed review grade. |
| `player_lines` | Repertoire, due dates, and the serialized FSRS state. |

</section>

<section class="card" id="present-and-inspect">

<!-- slide -->
<p class="slide-eyebrow">Team walkthrough</p>
<p class="slide-title">Run a review, then show what TEMPO saved</p>
<div class="slide-main"><div class="slide-row">
<div class="slide-tile is-term"><h4>PowerShell</h4><p>Run a clean review or a wrong-move retry.</p></div>
<div class="slide-tile"><h4>DB Browser</h4><p>Find the review and schedule by player ID.</p></div>
<div class="slide-tile"><h4>Offline CSV</h4><p>Show the synthetic sessions available for training.</p></div>
</div></div>
<p class="slide-scope">Terminal demo uses simulated timing · browser gameplay is implemented separately</p>
<!-- /slide -->

## Run, inspect, and explain the training data

In PowerShell, from the TEMPO repository root:

```powershell
.\backend\run-demo.cmd
.\backend\run-demo.cmd --side black --grade Again
```

The first command runs a clean Both-side review graded Good. The second demonstrates a wrong move and retry graded Again. Use the printed player ID to find the run in `backend/tempo_demo.sqlite` with **DB Browser for SQLite**. The terminal prints stability in days and the next review time in UTC. An initial FSRS learning step can make the next review due in minutes; the schedule is not a guarantee of an exact target-recall crossing. Terminal timings are simulated and do not measure browser interaction or human memory.

The historical `backend/synthetic_reviews.csv` export is recorded as 50,400 sessions from 30 simulated agents on 140 representative lines. It was not regenerated after catalog cleaning. The presentation generator reads the catalog without inserting synthetic practice events into SQLite, and follows the [Review Dataset](review-dataset.html) schema. Its output is separate from the run that supplied the app's fitted weights.

The maintained `ml/tempo_ml/` package provides independent generation, fitting and evaluation; [Synthetic Clients](synthetic-clients.html) explains its assumptions. The [offline training record](../topics/whole-flow/whole-flow.md#4-generate-offline-training-data) links methods and evidence. The app consumes a configured weights file; it does not launch fitting, import the newest experiment automatically or fine-tune on live player history.

This walkthrough reflects source inspected at `5d6b81c` on 2026-11-15. No application runtime checks were rerun for this documentation audit.

</section>
