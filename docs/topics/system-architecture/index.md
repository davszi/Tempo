+++
title = "System Architecture"
slug = "system-architecture"
description = "Trace browser requests, Python controllers, SQLite storage and the boundary to offline training."
toc = []
components = ["toc", "nav", "filelinks"]
page_css = ["build-sheet.css"]
+++

# System Architecture

<section class="card" id="components">

<span id="tempo-system-architecture"></span>

<span id="components-and-deployment"></span>

## A local browser app shares one SQLite practice record

<p class="bs-lead">The browser sends moves over HTTP; Python controllers coordinate practice, scheduling and persistence.</p>

<a href="#architecture-diagram">Figure 1</a> separates requests, responses and offline transfers. The browser owns display and input; the backend checks moves and writes outcomes.

<figure id="architecture-diagram">
<div role="region" aria-label="Scrollable TEMPO component diagram" tabindex="0" data-reader-horizontal style="overflow-x:auto">
<div style="min-width:900px">
<img src="../figures/tempo-system-architecture.svg" alt="The React browser calls the local Python backend over HTTP. Practice and ML controllers share SQLite. Synthetic generation and FSRS fitting run offline; selecting runtime weights is a separate explicit transfer." style="display:block;width:100%;min-width:900px;height:auto">
</div>
</div>
<figcaption><strong>Figure 1.</strong> Solid blue arrows show requests, dashed arrows responses, and green arrows offline data or weight transfers. The final weight transfer is an explicit configuration choice. Source: the architecture topic's <a href="../topics/system-architecture/component-flow.mmd">component flow</a> and <a href="../topics/system-architecture/system-architecture.html#component-diagram">source-authored drawing</a>.</figcaption>
</figure>

| Component | Current responsibility |
|---|---|
| React browser | Catalog, lessons, schedules and appearance; submits moves and renders returned session state. |
| HTTP handler | Routes JSON requests, validates demo player UUIDs, and can serve the built frontend. |
| Practice controller | Owns active sessions, checks attempts, records events and coordinates session completion. |
| ML controller | Reads repertoire/card state and review attempts; records suggestions and saves schedule updates. |
| ML engine | Selects due lines, grades attempts and uses Py-FSRS for card updates and recall estimates. |
| SQLite store | Catalog, practice events and per-player repertoire/schedule state. |

The Python server binds loopback HTTP at <code>127.0.0.1:8000</code>. Vite proxies API requests in development and preview; alternatively the backend serves built frontend files. The API uses a shared threaded controller; it can serve built frontend files directly. Changing the backend port alone does not change Vite’s fixed development proxy target. Hosted HTTPS and provisioned deployment storage remain proposals. This local server does not provide authentication.

The <a href="whole-flow.html">App & Practice overview</a> explains screens and the player journey. The <a href="opening-catalog.html">Catalog & Data overview</a> locates persisted records. Full boundaries and source paths remain in the <a href="docs.topics.system-architecture.system-architecture.md.html#components-and-deployment">architecture record</a>.

</section>

<section class="card" id="practice">

<span id="learning-and-repeating"></span>

## A review turns recorded attempts into one saved schedule update

<p class="bs-lead">Selection reads repertoire rows; completion reads the current session's attempts and saved FSRS card.</p>

<a href="#runtime-review">Figure 2</a> follows those two requests. Storing a suggestion does not mean the selector learns from suggestion history.

<figure id="runtime-review">
<div class="bs-flow">
<div class="bs-node"><span class="bs-label">Start review</span><b>Load repertoire</b><small>The ML controller reads this player's lines and due dates.</small></div>
<div class="bs-arrow"><span>select due</span></div>
<div class="bs-node"><span class="bs-label">ML engine</span><b>Choose one line</b><small>Earliest due date; ties use learned date, then line ID. No due line returns none_due.</small></div>
<div class="bs-arrow"><span>record</span></div>
<div class="bs-node"><span class="bs-label">Practice controller</span><b>Open session</b><small>A line_suggested event records the normal planner-selected path. The browser supplies the family side.</small></div>
</div>
<div class="bs-flow">
<div class="bs-node"><span class="bs-label">Finish review</span><b>Read attempts & card</b><small>Attempts belong to this player, line and session; the card comes from player_lines.</small></div>
<div class="bs-arrow"><span>grade</span></div>
<div class="bs-node"><span class="bs-label">ML engine + Py-FSRS</span><b>Update card</b><small>Any wrong attempt gives Again. Otherwise timing determines the grade. FSRS returns a new card and due time.</small></div>
<div class="bs-arrow"><span>commit</span></div>
<div class="bs-node"><span class="bs-label">One transaction</span><b>Save completion</b><small>The final attempt, completed review event and updated progress commit together.</small></div>
</div>
<figcaption><strong>Figure 2.</strong> Arrows show calls and data flow within review start and completion. Empty repertoire returns learn_first. Source: <a href="docs.topics.system-architecture.system-architecture.md.html#human-overview-and-figure-sources">controller and engine provenance</a>; diagram authored in this page.</figcaption>
</figure>

| Selection condition | Result |
|---|---|
| No repertoire rows for this player | Return <code>learn_first</code>; no session opens and no suggestion is logged. |
| Repertoire exists but no saved date is due | Return <code>none_due</code>; no session opens and no suggestion is logged. |
| At least one line is due | Choose the smallest due date, then learned date, then line ID; log the suggestion and open a session awaiting side. |

The selector compares saved dates with server UTC now. It uses repertoire rows, not the complete practice-event or suggestion history. Per-player card state evolves with reviews; learned ranking and live fine-tuning remain intended capabilities. First Learning creates an unreviewed card due at 04:00 on the player's next local day. Later Learning leaves that card and its schedule intact.

Review timing starts at side selection or a resumed session, resets after each attempt and uses elapsed server monotonic time. Request/UI waiting and idle time count; time before side selection does not. For a clean review, the engine divides total response time by the number of distinct attempted move indices, then subtracts its configured baseline. The web baseline is zero.

| Review condition | Grade |
|---|---|
| Any wrong attempt, even after correction | Again |
| Clean adjusted mean below 500 ms | Easy |
| Clean adjusted mean from 500 through 1,800 ms | Good |
| Clean adjusted mean above 1,800 ms | Hard |

These are the implemented app rules, not validated human-memory cutoffs. A new grading rule was decided on 2026-11-16 but is not implemented yet: one mistake no longer means Again on lines of 4 moves or more, and time is measured in the browser without a baseline. The app keeps the rules above until then. <a href="session-grading.html">Session grading</a> explains the decided rule.

A due timestamp is a scheduler output, not a guarantee of an exact target-recall crossing. FSRS learning or relearning steps may schedule reviews sooner than stability in days suggests. The <a href="docs.topics.system-architecture.system-architecture.md.html#review-scheduling">scheduling record</a> owns timing and dependency limits.

Direct-line reviews bypass selection; review mistake hints also conflict with the accepted contract. These remain <a href="docs.topics.app-practice.app-practice.md.html#unresolved-repeating-behavior">unresolved implementation deviations</a>. See the <a href="whole-flow.html#learning-to-schedule">practice journey</a> for interruption, re-learning and storage behavior.

</section>


<section class="card" id="session-transactions">

## Database completion happens before the active session advances

<p class="bs-lead">The controller serializes session mutations; a completed review's events and saved card share one database transaction.</p>

<figure id="completion-boundary">
<div class="bs-flow">
<div class="bs-node"><span class="bs-label">Shared controller lock</span><b>Check session & index</b><small>One active session per player. Start, side choice, moves and early close are serialized across players.</small></div>
<div class="bs-arrow"><span>write</span></div>
<div class="bs-node"><span class="bs-label">SQLite transaction</span><b>Persist attempt & result</b><small>A final move also writes completion and initializes Learning progress or updates the review card.</small></div>
<div class="bs-arrow"><span>commit first</span></div>
<div class="bs-node"><span class="bs-label">Process memory</span><b>Advance or remove</b><small>Only after the write succeeds does the controller change the move position or remove the completed session.</small></div>
</div>
<figcaption><strong>Figure 3.</strong> Arrows show ordering across persistence and process memory. The lock does not coordinate separate server processes. Generator: this page's HTML; input: <a href="docs.topics.system-architecture.system-architecture.md.html#session-and-transaction-boundaries">session and transaction source review</a>.</figcaption>
</figure>

<a href="#completion-boundary">Figure 3</a> identifies the failure boundary: a failed write does not intentionally advance the in-memory session. A successful commit followed by a lost response is different—the client may fall behind committed state, and there is no request-ID/idempotency recovery mechanism.

The threaded local server shares one Practice controller. Its lock protects session-changing operations; catalog and repertoire reads do not take that lock. Sessions have no persistence or expiry and cannot span multiple server processes. Starting another valid line replaces that player's active session. An empty/no-due planner result leaves it alone.

An unfinished session can leave move events without a completion. Ordinary abandonment updates no schedule. Explicit early close requires a running review with a persisted wrong attempt; it commits an Again completion and new schedule before deleting the session. Browser-local Learning saves reopen a new session, as explained in <a href="whole-flow.html#resume-and-identity">App & Practice</a>.

Exact UCI equality against the prescribed sequence decides correctness. The controller does not evaluate alternative chess moves. Single-side play includes scripted opponent replies; Both-side play advances a single ply. The <a href="opening-catalog.html#storage-operations">store transaction explanation</a> covers connections, write locking and catalog upgrades.

</section>

<section class="card" id="live-demo">

<span id="run-the-demo"></span>

## Offline fitting supplies weights through an explicit choice

<p class="bs-lead">The app loads configured FSRS weights; experiments run outside the live practice request.</p>

<a href="#weight-boundary">Figure 4</a> shows where the offline pipeline ends and the runtime begins. New experiment results do not change the app automatically.

<figure id="weight-boundary">
<div class="bs-flow">
<div class="bs-node"><span class="bs-label">Offline · ml/tempo_ml</span><b>Generate & fit</b><small>Synthetic clients produce datasets. Training and evaluation create dated experiment outputs.</small></div>
<div class="bs-arrow"><span>choose</span></div>
<div class="bs-node"><span class="bs-label">Configuration boundary</span><b>Select weights CSV</b><small>The app uses its configured file. Its supplied default is backend/fitted_global.csv.</small></div>
<div class="bs-arrow"><span>load</span></div>
<div class="bs-node"><span class="bs-label">Runtime backend</span><b>Schedule reviews</b><small>Py-FSRS uses the loaded weights and each player's saved card. It does not launch the fitter.</small></div>
</div>
<figcaption><strong>Figure 4.</strong> Arrows are offline output selection and startup loading, not an automatic model-refresh service. Source: <a href="docs.topics.system-architecture.system-architecture.md.html#components-and-deployment">runtime/offline boundary</a> and <a href="docs.topics.fsrs-training.fsrs-training.md.html">training provenance</a>; diagram authored in this page.</figcaption>
</figure>

The configured CSV must have ordered <code>w0</code> through <code>w20</code> columns, a complete row and finite numeric values. Loading also rejects weights that Py-FSRS would adjust. The web and terminal entrypoints explicitly supply the demo CSV; direct backend construction without a weights file uses dependency defaults. The <a href="docs.topics.system-architecture.system-architecture.md.html#weight-and-dependency-boundary">weight/dependency contract</a> owns these checks and the unpinned allowed dependency range.

The engine deserializes the player's saved card, passes it with grade and review time to Py-FSRS, and serializes the returned card. Displayed stability and recall come from that card. The app supplies no custom learning steps or fuzzing settings; exact dependency defaults and installed-version behavior were not verified in this source audit.

The maintained generation, fitting and evaluation package lives in <code>ml/tempo_ml/</code>. The backend's presentation CSV generator is a separate historical path. Neither runs inside a browser review request, and the supplied runtime weights are not automatically replaced by newer experimental weights.

For commands and inspection by player ID, use <a href="whole-flow.html#present-and-inspect">Start the app and inspect what practice saves</a>. The terminal demo uses simulated timing; running it does not establish human calibration or live personalization. Continue to <a href="synthetic-clients.html">Synthetic Clients</a> and <a href="fsrs-training.html">FSRS Training</a> for assumptions, methods and dated results.

This overview uses source inspection at <code>788e060</code>; it does not claim a fresh app run or production deployment check.

</section>
