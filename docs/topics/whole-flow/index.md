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
<div class="slide-tile is-term"><h4>Opening catalog</h4><p>3,865 lines across 140 families</p></div>
<div class="slide-tile"><h4>SQLite</h4><p>Stores the move sequences and player progress</p></div>
<div class="slide-tile"><h4>FSRS configuration</h4><p>21 supplied weights loaded from CSV</p></div>
</div></div>
<p class="slide-scope">Local presentation setup</p>
<!-- /slide -->

## Prepare the catalog and weights

The demo database contains 3,865 Lichess opening lines across 140 families. During import, the PGN sequences were converted to UCI and stored alongside names, ECO codes, and side classifications. The demo loads the 21 supplied weights from `backend/fitted_global.csv` at startup.

See the [system architecture](system-architecture.html) for the component diagram and proposed deployment.

</section>

<section class="card" id="learning-to-schedule">

<!-- slide -->
<p class="slide-eyebrow">Practice flow</p>
<p class="slide-title">Learning adds a line, and Repeating updates its schedule</p>
<div class="slide-main"><div class="slide-row">
<div class="slide-tile is-term"><h4>Learn</h4><p>Choose a line and practise with hints.</p></div>
<div class="slide-tile"><h4>Repeat</h4><p>Recall a due line without hints.</p></div>
<div class="slide-tile"><h4>Schedule</h4><p>Grade the review and save the next due date.</p></div>
</div></div>
<p class="slide-scope">Implemented in the Python backend</p>
<!-- /slide -->

## From Learning to the next review

1. The **practice controller** loads the chosen line, provides Learning hints, and records each attempt in SQLite. The first Learning completion adds the line to the repertoire and makes it immediately due.
2. The **ML controller** reads the repertoire, and the **ML engine** picks the most overdue line. The player chooses White, Black, or Both. During Repeating, a wrong move leaves the position unchanged so the player can retry.
3. The **ML engine** grades the finished review from the move attempts and timing. Py-FSRS uses that grade and the supplied weights to update stability and calculate the due date. The schedule and completion event are committed together.

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
<p class="slide-scope">Simulated response times · browser gameplay is planned</p>
<!-- /slide -->

## Run, inspect, and explain the training data

In PowerShell, from the TEMPO repository root:

```powershell
.\backend\run-demo.cmd
.\backend\run-demo.cmd --side black --grade Again
```

The first command runs a clean Both-side review. The second demonstrates a wrong move and retry. Use the printed player ID to find the run in `backend/tempo_demo.sqlite` with **DB Browser for SQLite**. The terminal prints stability in days and the next review time in UTC. An initial FSRS learning step can make the next review due in minutes.

The [Synthetic Clients](synthetic-clients.html) generate recall attempts and timing for offline training. The local `backend/synthetic_reviews.csv` contains 50,400 sessions from 30 simulated agents on one line per opening family. It follows the [Review Dataset](review-dataset.html) format and is separate from the run that produced the fitted weights.

</section>
