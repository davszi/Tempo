+++
title = "App & Practice"
slug = "whole-flow"
description = "Follow Learning and Repeating, what each screen does, and where practice progress is saved."
toc = []
components = ["toc", "nav", "filelinks"]
page_css = ["build-sheet.css"]
+++

# App & Practice

<section class="card" id="catalog">

<span id="tempo-end-to-end-flow"></span>

<span id="prepare-the-catalog-and-weights"></span>

## Keep the openings you have learned

<p class="bs-lead">Choose a line to learn; return to practise it when its saved schedule says it is due.</p>

<a href="#app-map">Figure 1</a> locates the app's screens around that practice cycle. The opening catalog supplies the lines; your repertoire contains the ones you have learned.

<figure id="app-map">
<div class="bs-flow">
<div class="bs-node"><span class="bs-label">Explore</span><b>Learning</b><ul><li>Search opening families and variations.</li><li>Filter by family side.</li><li>Choose a learnable line.</li></ul></div>
<div class="bs-arrow"><span>choose line</span></div>
<div class="bs-node"><span class="bs-label">Practise</span><b>Lesson board</b><ul><li>Follow move hints in Learning.</li><li>Try recalled moves in Repeating.</li><li>Wrong moves leave the position unchanged.</li></ul></div>
<div class="bs-arrow"><span>save result</span></div>
<div class="bs-node"><span class="bs-label">Return</span><b>Dashboard & repertoire</b><ul><li>See saved due dates and review history.</li><li>Resume an unfinished local lesson.</li><li>Start a due review.</li></ul></div>
</div>
<figcaption><strong>Figure 1.</strong> Arrows show the player's path through the app, not separate databases. The review queue also opens from navigation; Settings controls appearance. Source: <a href="docs.topics.frontend.frontend.md.html#screens-and-practice">frontend screens</a>; diagram authored in this page.</figcaption>
</figure>

Learning shows an arrow and notation for the expected move. Click, keyboard and drag interactions submit moves; the opponent's reply follows a correct move. The browser uses the opening family's side automatically. Backend and terminal callers also support White, Black or Both.

The dashboard shows a 30-day view of saved due dates, grouping overdue lines into today. It does not predict new dates after future practice. Repertoire shows learned lines, review grades and the latest fetched memory estimates. The displayed “days until forgetting” means time until a scheduled review, not a measured time when memory disappears.

The <a href="opening-catalog.html">Catalog & Data overview</a> explains which lines are learnable. The <a href="docs.topics.frontend.frontend.md.html#http-interface">frontend record</a> holds the API, screen details and display limits.

</section>

<section class="card" id="learning-to-schedule">

<span id="from-learning-to-the-next-review"></span>

## Learning adds a line; Repeating updates its schedule

<p class="bs-lead">Both modes write to one practice history, while only a completed review changes an existing review schedule.</p>

<a href="#practice-cycle">Figure 2</a> follows the normal planner-selected route. A newly learned line is due immediately; later Learning preserves its existing schedule.

<figure id="practice-cycle">
<div class="bs-flow">
<div class="bs-node"><span class="bs-label">Player chooses</span><b>Complete Learning</b><small>A new line joins the repertoire with an initial card due now.</small></div>
<div class="bs-arrow"><span>start review</span></div>
<div class="bs-node"><span class="bs-label">Planner chooses</span><b>Recall a due line</b><small>The normal Start review action selects the earliest due line and records a suggestion.</small></div>
<div class="bs-arrow"><span>complete</span></div>
<div class="bs-node"><span class="bs-label">Saved together</span><b>Grade & next date</b><small>The final attempt, completion event and FSRS schedule update commit in one transaction.</small></div>
</div>
<div class="bs-grid g2">
<div class="bs-part"><h3>Nothing to review?</h3><p>An empty repertoire leads back to Learning. If no line is due, the planner returns that state rather than choosing a future line.</p></div>
<div class="bs-part"><h3>Leaving a session</h3><p>Ordinary navigation away does not complete a review. Closing through re-learning after mistakes records Again and reschedules first.</p></div>
</div>
<figcaption><strong>Figure 2.</strong> Arrows mean session transitions; the final node is one database transaction. Source: <a href="docs.topics.whole-flow.whole-flow.md.html#2-learn-repeat-and-schedule">practice flow record</a>; diagram authored in this page.</figcaption>
</figure>

The settled Repeating contract requires planner-selected lines with no hints or arrows. The current browser also offers chosen-line reviews and reveals the expected move after the first mistake. These remain <a href="docs.topics.frontend.frontend.md.html#unresolved-repeating-behavior">unresolved deviations</a>. Direct-line review bypasses the planner suggestion event. They do not change the accepted contract through this overview.

Any wrong review attempt yields Again, even if corrected. Clean reviews are graded from server-recorded response time, including request waiting and idle time. The <a href="system-architecture.html#practice">runtime scheduling explanation</a> shows how a grade updates a card; <a href="review-dataset.html">Review Data & Grading</a> explains the grading rule and its calibration limits.

<a href="#storage-boundaries">Figure 3</a> explains why a browser can resume a lesson even though restarting the backend loses its active session.

<figure id="storage-boundaries">
<div class="bs-grid g3">
<div class="bs-part"><h3>This browser</h3><ul><li>Demo player UUID</li><li>Unfinished Learning positions</li><li>Appearance preferences</li></ul><p>A saved position opens a new backend session on resume.</p></div>
<div class="bs-part"><h3>Backend process</h3><ul><li>Active session and move position</li><li>One active session per player</li></ul><p>Restarting loses these sessions. They are not SQLite records.</p></div>
<div class="bs-part"><h3>SQLite file</h3><ul><li>Learned repertoire</li><li>Practice events</li><li>FSRS cards and due dates</li></ul><p>Completed practice survives browser and server restarts.</p></div>
</div>
<figcaption><strong>Figure 3.</strong> Columns are storage ownership boundaries. Browser-local identity is not authentication. Clearing it selects a new player; it does not delete the old SQLite history. Source: <a href="docs.topics.frontend.frontend.md.html#identity-and-persistence">frontend persistence</a>; diagram authored in this page.</figcaption>
</figure>

</section>

<section class="card" id="present-and-inspect">

<span id="run-inspect-and-explain-the-training-data"></span>

## Start the app and inspect what practice saves

<p class="bs-lead">Run the Python API and browser frontend together; use a copied database when you want to preserve the tracked seed.</p>

From the repository root, install and start the backend in one PowerShell window:

```powershell
python -m pip install -r backend/requirements.txt
python -m backend.web
```

In another window, start the frontend:

```powershell
cd frontend
npm.cmd ci
npm.cmd run dev
```

Open <a href="http://127.0.0.1:5173/">the local app</a>. The API listens on port 8000. The <a href="docs.project_context.md.html#build-and-review">setup guide</a> owns environment requirements and the separate documentation build.

For a repeatable terminal walkthrough, run from the repository root:

```powershell
.\backend\run-demo.cmd
.\backend\run-demo.cmd --side black --grade Again
```

The first command runs a clean Both-side review graded Good; the second demonstrates a wrong move and retry graded Again. The terminal prints a fresh player ID, grade, stability and the next due time in UTC. In DB Browser for SQLite, filter <code>practice_events</code> and <code>player_lines</code> by that ID. The terminal uses simulated timing and does not measure human recall or browser interaction. Pass a scratch database copy with <code>--database</code> to keep the tracked seed pristine.

The app consumes a configured weights file. Synthetic generation and model fitting run separately; the app does not automatically import the newest experiment or fit on live player history. Continue to <a href="system-architecture.html">System Architecture</a> for those boundaries, or <a href="fsrs-training.html">FSRS Training</a> for methods and dated evidence.

This overview follows source and records inspected at <code>dab04ac</code>. No application runtime or browser check was rerun for this presentation change.

</section>
