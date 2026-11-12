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
<p class="slide-lead">The browser connects over HTTPS, and the host keeps the SQLite file on persistent storage.</p>
<div class="slide-main">
  <div class="slide-row">
    <div class="slide-tile is-held"><h4>Player device</h4><p>Browser chess interface</p></div>
    <div class="slide-tile is-term"><h4>Application host</h4><p>Practice controller, ML controller, and ML engine</p></div>
    <div class="slide-tile"><h4>Persistent storage</h4><p>SQLite lines, progress, and practice history</p></div>
  </div>
</div>
<p class="slide-scope">Proposed deployment · browser integration and offline model fitting are planned</p>
<!-- /slide -->

## Components and deployment

<p class="bs-lead">The Python backend uses SQLite to share practice history between Learning and Repeating.</p>

<a href="#architecture-diagram">Figure 1</a> shows the proposed browser-to-host deployment and the data exchanged between components.

<figure id="architecture-diagram">
<div role="region" aria-label="Scrollable TEMPO component diagram" tabindex="0" style="overflow-x:auto">
<img src="../figures/tempo-system-architecture.svg" alt="A player browser connects over planned HTTPS to a single Python host with the practice controller, ML components, and a SQLite file on persistent storage. Synthetic training runs offline." style="display:block;width:100%;min-width:780px;height:auto">
</div>
<figcaption><strong>Figure 1.</strong> Solid blue arrows show requests, dashed arrows show responses, and green arrows show offline transfers. The browser connection and model fitting are planned. The backend and SQLite file share one application host.</figcaption>
</figure>

| Component | Responsibility |
|---|---|
| Practice controller | Loads the line, starts practice, checks submitted moves, and records events. |
| ML controller | Loads repertoire and review data from SQLite, calls the ML engine, and saves its result. |
| ML engine | Loads the supplied FSRS weights for the demo, selects a due line, assigns the review grade, and updates stability and the due date. |
| SQLite | Stores opening lines, player progress, and practice history. |
| Offline pipeline | Simulates players and writes graded review sessions to CSV. Fitting a general model from the CSV remains planned. |

</section>

<section class="card" id="practice">

<!-- slide -->
<p class="slide-eyebrow">Practice</p>
<p class="slide-title">The player chooses what to learn, and the planner chooses what to review</p>
<p class="slide-lead">The player chooses White, Black, or Both. The ML engine grades completed reviews and schedules the next one.</p>
<div class="slide-main">
  <div class="slide-row">
    <div class="slide-tile is-term"><h4>Learning</h4><p>Choose a line and follow move hints.</p></div>
    <div class="slide-tile"><h4>Repeating</h4><p>Open the due line, choose a side, and recall the moves.</p></div>
  </div>
</div>
<p class="slide-scope">Current backend behavior · the first review is due immediately after Learning</p>
<!-- /slide -->

## Learning and Repeating

- **Learning:** The player chooses a line and side. TEMPO shows the expected move and adds the line to the repertoire on completion.
- **Repeating:** The planner opens a due line, then the player chooses White, Black, or Both. In Both, the player makes every move in one run. The ML engine grades the completed session once and calculates the next due date.
- **First review:** A newly learned line is due immediately in the current backend. TEMPO directs players with an empty repertoire to Learning.

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
.\run-demo.cmd
.\run-demo.cmd --side black --grade Again
```

The first command runs a clean review using Both sides. The second demonstrates a wrong move and retry. Each prints the player ID, grade, stability in days, and next review time in UTC. An early FSRS learning step can schedule a review in minutes even when estimated stability is measured in days.

Open `demo/tempo_demo.sqlite` in **DB Browser for SQLite**. Use **Browse Data** to find `practice_events` and `player_lines`, then filter by the player ID printed in PowerShell.

`demo/fitted_global.csv` supplies the FSRS weights at runtime. `demo/synthetic_reviews.csv` contains 50,400 generated review sessions from 30 simulated agents, using one line per opening family. This CSV was generated separately from the training run that produced the supplied weights.

</section>
