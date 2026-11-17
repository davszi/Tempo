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
<figcaption><strong>Figure 1.</strong> Arrows show the player's path through the app, not separate databases. The review queue also opens from navigation; Settings controls appearance. Source: <a href="docs.topics.app-practice.app-practice.md.html#screens-and-practice">app screens</a>; diagram authored in this page.</figcaption>
</figure>

Learning shows an arrow and notation for the expected move. Click, keyboard and drag interactions submit moves; the opponent's reply follows a correct move. The browser uses the opening family's side automatically. Backend and terminal callers also support White, Black or Both.

The dashboard shows a 30-day view of saved due dates, grouping overdue lines into today. It does not predict new dates after future practice. Repertoire groups your learned lines by opening family; opening a family lists its learned lines first with their current recall, review grades and due dates, then lessons in progress and the family's other lines. The displayed “days until forgetting” means time until a scheduled review, not a measured time when memory disappears.

The <a href="opening-catalog.html">Catalog & Data overview</a> explains which lines are learnable. The <a href="docs.topics.app-practice.app-practice.md.html#http-interface">App &amp; Practice Reference</a> holds the API, screen details and display limits.

</section>

<section class="card" id="learning-to-schedule">

<span id="from-learning-to-the-next-review"></span>

## Learning adds a line; Repeating updates its schedule

<p class="bs-lead">Both modes write to one practice history, while only a completed review changes an existing review schedule.</p>

<a href="#practice-cycle">Figure 2</a> follows the normal planner-selected route. A newly learned line is first due at 04:00 on the player's next local day, and until then it can only be practised without hints; later Learning preserves its existing schedule.

<figure id="practice-cycle">
<div class="bs-flow">
<div class="bs-node"><span class="bs-label">Player chooses</span><b>Complete Learning</b><small>A new line joins the repertoire with its first test due on your next day.</small></div>
<div class="bs-arrow"><span>start review</span></div>
<div class="bs-node"><span class="bs-label">Planner chooses</span><b>Recall a due line</b><small>The normal Start review action selects the earliest due line and records a suggestion.</small></div>
<div class="bs-arrow"><span>complete</span></div>
<div class="bs-node"><span class="bs-label">Saved together</span><b>Grade & next date</b><small>The final attempt, completion event and FSRS schedule update commit in one transaction.</small></div>
</div>
<div class="bs-grid g2">
<div class="bs-part"><h3>Nothing to review?</h3><p>An empty repertoire leads back to Learning. If no line is due, the planner returns that state rather than choosing a future line.</p></div>
<div class="bs-part"><h3>Leaving a session</h3><p>Ordinary navigation away does not complete a review. Closing through re-learning after mistakes records Again and reschedules first.</p></div>
</div>
<figcaption><strong>Figure 2.</strong> Arrows mean session transitions; the final node is one database transaction. Source: <a href="docs.topics.app-practice.app-practice.md.html#end-to-end-flow">practice flow record</a>; diagram authored in this page.</figcaption>
</figure>

The settled Repeating contract requires planner-selected lines with no hints or arrows. The current browser also offers chosen-line reviews and reveals the expected move after the first mistake. These remain <a href="docs.topics.app-practice.app-practice.md.html#unresolved-repeating-behavior">unresolved deviations</a>. Direct-line review bypasses the planner suggestion event. They do not change the accepted contract through this overview.

Any wrong review attempt yields Again, even if corrected. Clean reviews are graded from server-recorded response time, including request waiting and idle time. The <a href="system-architecture.html#practice">runtime scheduling explanation</a> shows how a grade updates a card; <a href="review-dataset.html">Review Data & Grading</a> explains the grading rule and its calibration limits.

<a href="#storage-boundaries">Figure 3</a> explains why a browser can resume a lesson even though restarting the backend loses its active session.

<figure id="storage-boundaries">
<div class="bs-grid g3">
<div class="bs-part"><h3>This browser</h3><ul><li>Demo player UUID</li><li>Unfinished Learning positions</li><li>Appearance preferences</li></ul><p>A saved position opens a new backend session on resume.</p></div>
<div class="bs-part"><h3>Backend process</h3><ul><li>Active session and move position</li><li>One active session per player</li></ul><p>Restarting loses these sessions. They are not SQLite records.</p></div>
<div class="bs-part"><h3>SQLite file</h3><ul><li>Learned repertoire</li><li>Practice events</li><li>FSRS cards and due dates</li></ul><p>Completed practice survives browser and server restarts.</p></div>
</div>
<figcaption><strong>Figure 3.</strong> Columns are storage ownership boundaries. Browser-local identity is not authentication. Clearing it selects a new player; it does not delete the old SQLite history. Source: <a href="docs.topics.app-practice.app-practice.md.html#identity-and-persistence">browser persistence</a>; diagram authored in this page.</figcaption>
</figure>

</section>


<section class="card" id="board-input">

## The board advances only after the server accepts the prescribed move

<p class="bs-lead">Click, keyboard and drag input all submit a move to the same backend session; the response supplies the displayed position.</p>

<figure id="board-request">
<div class="bs-flow">
<div class="bs-node"><b>Choose from / to</b><small>Use square buttons or pointer dragging. Promotion asks for a piece before submission.</small></div>
<div class="bs-arrow"><span>send UCI</span></div>
<div class="bs-node"><b>Check session & move</b><small>The server matches the session, full-line move index and exact prescribed UCI string.</small></div>
<div class="bs-arrow"><span>respond</span></div>
<div class="bs-node"><b>Reconstruct board</b><small>A correct response advances. A wrong attempt keeps the position; single-side play includes the scripted reply.</small></div>
</div>
<figcaption><strong>Figure 4.</strong> Arrows are request/response order. There is no optimistic browser move before acceptance. Generator: this page's HTML; input: <a href="docs.topics.app-practice.app-practice.md.html#board-input-and-feedback">board input and feedback source review</a>.</figcaption>
</figure>

<a href="#board-request">Figure 4</a> explains why an unexpected destination does not play out a punishment line. The live board sends coordinate UCI directly; it is checking repertoire recall, not asking a chess engine whether another move is good. Castling uses the king's source and destination squares; position reconstruction also moves the rook.

| Input or state | Current behavior |
|---|---|
| Square selection | Choose a piece of the side to move, then a destination; selecting another friendly piece changes selection. Native square buttons support keyboard focus and Enter/Space. |
| Dragging | Primary-pointer movement beyond <code>5 px</code> starts a drag. Cancelling, releasing off-board or returning to the source sends no attempt. |
| Promotion | Choose Queen, Rook, Bishop or Knight; the UCI suffix is sent only after that choice. Cancel clears it. |
| Waiting | Requests, Learning reply animation, promotion and the second-mistake decision block input. Completion blocks further moves. |
| Board perspective | Black sessions place Black at the bottom and include White's opening move. The browser takes the family's side; backend/demo callers can also choose Both. |

Learning supplies the move arrow and notation. Repeating currently reveals an arrow after the first mistake; the second mistake offers re-learning or continuation without further hints. After continuing, two more mistakes bring up a prompt with only Learn this line again. That feedback remains an <a href="docs.topics.app-practice.app-practice.md.html#unresolved-repeating-behavior">unresolved departure from the settled no-hints contract</a>. Keyboard square activation exists; a separate arrow-key board navigation system does not.

</section>

<section class="card" id="resume-and-identity">

## A saved lesson resumes a position, not the old active session

<p class="bs-lead">Browser-local Learning progress can reopen a new session; unfinished reviews have no durable resume.</p>

<figure id="lesson-resume">
<div class="bs-flow">
<div class="bs-node"><b>Correct Learning move</b><small>A successful non-final response saves line, ply and side in this browser.</small></div>
<div class="bs-arrow"><span>later start</span></div>
<div class="bs-node"><b>Read saved position</b><small>The saved side must match the family's current side; the browser requests resume_at.</small></div>
<div class="bs-arrow"><span>validate</span></div>
<div class="bs-node"><b>New backend session</b><small>The index must belong to the line and selected side. Timing starts again; earlier attempts keep their old session.</small></div>
</div>
<figcaption><strong>Figure 5.</strong> Arrows mean save and resume steps; they do not reconstruct a vanished process session. Generator: this page's HTML; input: <a href="docs.topics.app-practice.app-practice.md.html#saved-lessons-and-interrupted-sessions">saved-lesson implementation</a>.</figcaption>
</figure>

<a href="#lesson-resume">Figure 5</a> separates the locally saved position from the backend's active session. Wrong attempts alone create no Learning save. Completion clears it; Start over clears it before opening a new session. Later Learning does not reset an already learned line's review schedule.

An invalid saved position is cleared and the browser reports that the lesson starts again. That failure branch does not itself send another start request or open the lesson; the next explicit start begins from scratch. The save validates an index, not a replay of the earlier moves.

Shell navigation can unmount the lesson while the app retains its initial response. Returning through a lesson hash or browser history can therefore show an earlier position or reset hint state after the backend has advanced. A later move may be rejected for a stale index or a closed session. This is a source-derived failure possibility, not an executed browser failure.

Starting another session replaces this player's active backend session. Leaving through Back or navigation keeps any recorded attempts but adds no completion or schedule update. Completing a session or explicitly closing a mistaken review removes it. Restarting the backend loses all active sessions; a lesson URL alone cannot recover one.

The demo player UUID, preferences and unfinished lessons live under this browser origin. They do not synchronize across browsers or open tabs, and lesson/preferences keys are not separated by player UUID. Clearing only the player ID leaves those local preferences and saves. The ID selects stored records; it supplies no password or authentication. See <a href="#storage-boundaries">Figure 3</a> for the three storage boundaries and <a href="docs.topics.app-practice.app-practice.md.html#identity-and-persistence">Reference</a> for cache failure limits.

</section>

<section class="card" id="requests-and-memory">

## Saved dates and recall snapshots answer different questions

<p class="bs-lead">The schedule shows when a review is saved as due; recall is the FSRS estimate for right now, recomputed every minute.</p>

<div class="scroll" role="region" aria-label="Memory and schedule display meanings; scroll horizontally on narrow screens" tabindex="0" data-reader-horizontal style="overflow-x:auto">
<div style="min-width:640px">

| Display | What it means | Limit |
|---|---|---|
| Due / future | Compare the saved due timestamp with the browser clock. | The server's returned time does not drive the browser's due labels. |
| Day countdown | Compare dates in the browser's local time zone. | “Days until forgetting” is time until a scheduled review, not measured memory loss. |
| Recall and stability | Derive estimates from the saved FSRS card; the browser recomputes recall each minute from stability and the last review time. | Recall is a model estimate, not measured memory; both are absent before first review. The “new”/striped bar style is not observed perfect recall. |
| Dashboard calendar | Show saved due dates across the display horizon, with overdue work in today. | It does not simulate future practice. Fixed-day bins were not verified across daylight-saving transitions. |
| Review history | Show completed grades and elapsed days between learning/reviews. | Bar lengths are not past stability measurements. |

</div>
</div>


Opening memory screens and completing sessions refreshes repertoire data. Due labels and recall percentages both refresh against the browser clock each minute. The <a href="docs.topics.app-practice.app-practice.md.html#memory-displays-and-limits">display record</a> details date bins and target-color bands; <a href="system-architecture.html#practice">runtime scheduling</a> explains the card update behind those dates.

The browser uses relative <code>/api/</code> requests carrying its player UUID. Catalog/repertoire failures show a Retry banner; session failures show a toast. JSON errors surface the server message, and a non-JSON response gives a backend-start message. The client supplies no automatic retry, timeout or response-shape validation. The <a href="docs.topics.app-practice.app-practice.md.html#http-interface">HTTP Reference</a> holds endpoint/field lookup and <a href="docs.topics.app-practice.app-practice.md.html#validation-and-failure-boundaries">validation/error details</a>.

A move request includes the active session and current full-line index. If persistence succeeds but its response is lost, resending is not an idempotent recovery: the server may already have advanced or closed the session. This failure implication follows inspected control flow; network-loss recovery and corrupted-storage cases were not exercised in this documentation pass.

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

This overview follows source and records inspected at <code>788e060</code>. No application runtime or browser check was rerun for this presentation change.

</section>
