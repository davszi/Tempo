+++
title = "TEMPO System Architecture"
slug = "system-architecture"
toc = []
components = ["toc", "nav", "filelinks"]
page_css = ["build-sheet.css"]
+++

# TEMPO System Architecture

<section class="card" id="components">

<!-- slide -->
<p class="slide-eyebrow">Deployment</p>
<p class="slide-title">One Python host runs the practice backend</p>
<p class="slide-lead">The React browser app calls the Python backend over local HTTP; SQLite holds shared practice history.</p>
<div class="slide-main">
  <div class="slide-row">
    <div class="slide-tile"><h4>Player device</h4><p>React browser chess interface</p></div>
    <div class="slide-tile is-term"><h4>Application host</h4><p>Practice controller, ML controller, and ML engine</p></div>
    <div class="slide-tile"><h4>Local storage</h4><p>SQLite lines, progress, and practice history</p></div>
  </div>
</div>
<p class="slide-scope">Implemented local app · hosted HTTPS remains proposed · offline fitting is separate</p>
<!-- /slide -->

## Components and deployment

<p class="bs-lead">The browser, Python controllers and SQLite implement a local practice app; offline FSRS fitting runs separately.</p>

<a href="#architecture-diagram">Figure 1</a> shows the component boundaries and data exchanged between them. The Python server uses loopback HTTP; Vite proxies API requests during development, or the backend serves the built frontend. Hosted HTTPS and persistent deployment storage remain proposals. The <a href="../topics/system-architecture/system-architecture.md#components-and-deployment">architecture record</a> owns these boundaries and source references.

<figure id="architecture-diagram">
<div role="region" aria-label="Scrollable TEMPO component diagram" tabindex="0" style="overflow-x:auto">
<div style="min-width:900px">
<img src="../figures/tempo-system-architecture.svg" alt="The React browser calls the local Python backend over HTTP. Practice and ML controllers share a SQLite file. Synthetic generation and FSRS fitting run offline, and weight selection for the app is separate." style="display:block;width:100%;min-width:900px;height:auto">
</div>
</div>
<figcaption><strong>Figure 1.</strong> Solid blue arrows show requests, dashed arrows responses, and green arrows offline data or weight transfers. The final weight transfer is an explicit configuration choice, not an automatic import. Source: the architecture topic's <a href="../topics/system-architecture/component-flow.mmd">component flow</a> and <a href="../topics/system-architecture/system-architecture.html#component-diagram">source-authored drawing</a>.</figcaption>
</figure>

| Component | Responsibility |
|---|---|
| React browser and HTTP handler | Render catalog, lessons and schedules; exchange JSON session state. The Python handler can serve the built frontend. |
| Practice controller | Loads the line, starts practice, checks submitted moves, and records events. |
| ML controller | Loads repertoire and review data from SQLite, calls the ML engine, and saves its result. |
| ML engine | Loads supplied FSRS weights, selects the earliest due repertoire line, grades the review, and delegates card updates and recall estimates to Py-FSRS. |
| SQLite | Stores opening lines, player progress, and practice history. |
| Offline pipeline | The maintained `ml/tempo_ml/` package generates data, fits FSRS-6 and evaluates weights. The backend presentation generator is separate. |

The selector reads repertoire rows. It stores suggestions but does not use suggestion history or the complete event history to choose a line. A learned planner and live per-player fine-tuning remain intended capabilities; the app does not launch fitting or automatically import the newest experiment.

</section>

<section class="card" id="practice">

<!-- slide -->
<p class="slide-eyebrow">Practice</p>
<p class="slide-title">Learning and Repeating share the same practice history</p>
<p class="slide-lead">Learning adds repertoire lines; completed reviews update their FSRS cards. The browser uses each opening family's side.</p>
<div class="slide-main">
  <div class="slide-row">
    <div class="slide-tile is-term"><h4>Learning</h4><p>Choose a line and follow move hints.</p></div>
    <div class="slide-tile"><h4>Repeating</h4><p>Normal Start review opens a due line and records the outcome.</p></div>
  </div>
</div>
<p class="slide-scope">First review due immediately · direct-line reviews and mistake hints remain unresolved deviations</p>
<!-- /slide -->

## Learning and Repeating

- **Learning:** The player chooses a learnable line. The browser supplies the family side; backend/demo callers can choose White, Black or Both. TEMPO shows the expected move and adds a new line to the repertoire on completion. Re-learning preserves its existing schedule.
- **Repeating:** Normal Start review picks the earliest due line, then earliest learned date and line ID to break ties. The browser supplies the family side. The engine grades completion and calculates the next due date.
- **First review:** A newly learned line is due immediately in the current backend. TEMPO directs players with an empty repertoire to Learning.

The settled contract requires planner-selected reviews without hints or arrows. The current browser also lets players select learned lines directly and shows the expected move after the first mistake. Both are <a href="../topics/frontend/frontend.md#unresolved-repeating-behavior">unresolved deviations</a>, not approved changes to the contract. Wrong moves leave the position unchanged in both paths. Direct-line review bypasses the planner suggestion event.

Active sessions live in the backend process and disappear at restart. Browser-local unfinished Learning progress can start a resumed session; navigating away from Repeating does not complete or grade it. A final correct attempt, review completion and schedule update share one transaction; early close after a recorded mistake also completes the review as Again. See <a href="../topics/system-architecture/system-architecture.md#review-scheduling">review scheduling</a> for timing and grading limits.

</section>

<section class="card" id="live-demo">

<!-- slide -->
<p class="slide-eyebrow">Live demo</p>
<p class="slide-title">One practice run produces a grade and saves the next review</p>
<p class="slide-lead">The demo loads the supplied FSRS weights and walks through Learning and Repeating on a Lichess opening line.</p>
<div class="slide-main">
  <div class="slide-row">
    <div class="slide-tile is-term"><h4>Run</h4><p>Start the Python demo from the repo root.</p></div>
    <div class="slide-tile"><h4>Read</h4><p>See the grade, stability, and next review time.</p></div>
    <div class="slide-tile"><h4>Inspect</h4><p>Find the saved review by player ID in SQLite.</p></div>
  </div>
</div>
<p class="slide-scope">Simulated move timing · supplied FSRS weights · local SQLite database</p>
<!-- /slide -->

## Run the demo

For the full walkthrough from catalog import to the saved review, open the [End-to-End Flow](whole-flow.html).

From the TEMPO repo root in PowerShell, run:

```powershell
.\backend\run-demo.cmd
.\backend\run-demo.cmd --side black --grade Again
```

The first command runs a clean review using Both sides. The second demonstrates a wrong move and retry. Each prints the player ID, grade, stability in days, and next review time in UTC. An early FSRS learning step can schedule a review in minutes even when estimated stability is measured in days.

Open `backend/tempo_demo.sqlite` in **DB Browser for SQLite**. Use **Browse Data** to find `practice_events` and `player_lines`, then filter by the player ID printed in PowerShell.

`backend/fitted_global.csv` supplies the 21 FSRS weights at runtime. The historical `backend/synthetic_reviews.csv` export is recorded as 50,400 sessions from 30 agents on 140 representative lines. It was not regenerated after catalog cleaning and merges, and is separate from the run that produced the supplied weights. The <a href="../topics/system-architecture/system-architecture.md#presentation-demo">demo record</a> and <a href="../topics/fsrs-training/fsrs-training.md">FSRS training record</a> own its provenance and limits.

This explanation follows source inspection at `5d6b81c` on 2026-11-15. The documentation audit did not rerun the app or establish production deployment, human calibration or live personalization.

</section>
