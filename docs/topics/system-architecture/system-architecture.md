# TEMPO system architecture

This record describes source at `788e06039dd2869b23261dd80ea8fc49367ab33c`, inspected on 2026-11-15, and separates implemented local mechanisms from accepted requirements, proposals and runtime evidence. Learning and Repeating use a Python backend and shared SQLite practice history. [Project context](../../PROJECT_CONTEXT.md) owns terminology and settled requirements; [App & Practice](../app-practice/app-practice.md) owns browser routes, HTTP contracts, board behavior, persistence/resume and the unresolved Repeating deviations. [Catalog & Data](../catalog-data/catalog-data.md) owns store operations, schema and catalog provenance.

## Components and deployment

The [architecture diagram](component-flow.mmd) connects the browser, practice backend, SQLite and offline training. The current local web server binds HTTP to `127.0.0.1:8000`; Vite proxies `/api` from development/preview, or the Python server serves built `frontend/dist`. These mechanisms are implemented in `backend/web.py` and `frontend/vite.config.ts`. Hosted HTTPS and persistent deployment storage remain proposals, not features of the local HTTP server.

`web.main` accepts `--database`, `--weights` and `--port`; its defaults are
`backend/tempo_demo.sqlite`, `backend/fitted_global.csv` and 8000. It rejects a
missing database or weights file before constructing a backend. Binding remains
loopback even with a custom port. `Handler` subclasses Python's
`SimpleHTTPRequestHandler`, serving non-API GETs from `frontend/dist` and JSON
API responses with `Cache-Control: no-store`. The app's hash navigation needs
no server rewrite for browser routes. Vite's proxy target is fixed to port
8000, so changing the Python port alone does not change development routing.

The HTTP server is a `ThreadingHTTPServer` sharing one `PracticeController`.
It is a local demonstration runtime, with no implemented account authentication,
HTTPS termination, distributed session store, cross-process coordination,
deployment storage provisioning or automatic model rollout. Serving a built
frontend is an implemented option; production readiness was not assessed.

| Component | Current responsibility and source |
|---|---|
| Chess UI | React catalog, lesson, schedule, repertoire and settings screens; calls the API and renders server session state. `frontend/src/App.tsx`, `frontend/src/components/` |
| HTTP handler | Dispatches JSON requests to a shared controller, normalizes UUID player IDs and serves the built frontend. `backend/web.py` |
| Practice controller | Owns one active in-memory session per player, loads lines, checks attempts, supplies feedback, records events, and requests a review line. It also exposes direct-line review, resume and early close. `backend/practice_controller.py` |
| SQLite store | Opening families/lines, practice events and player progress. Short-lived connections, foreign-key enforcement and write transactions; catalog upgrades preserve practice references. `backend/store.py` |
| ML controller | Loads `player_lines` for selection and records planner suggestions; initializes first-learning progress; loads a saved FSRS card and the current session's attempts to complete a review. `backend/ml_controller.py` |
| ML engine | Selects the earliest due repertoire line, grades attempts, and delegates card updates and recall estimates to Py-FSRS. Loads a supplied 21-weight CSV or dependency defaults. `backend/ml_engine.py` |
| Offline generation and fitting | The maintained `ml/tempo_ml/` package generates synthetic data, fits FSRS-6 and evaluates weights. `backend/synthetic_clients.py` is a separate presentation-data generator. The web app does not run either pipeline or automatically replace its weights from experiment output. |

The ML controller stores suggestions but does not read suggestion history for selection. The current selector receives repertoire rows, not the complete practice-event history. A learned planner that consumes past suggestions and per-player fine-tuning are intended capabilities, not current web behavior. Offline training exists; [FSRS training](../fsrs-training/fsrs-training.md) owns its methods, results and limits.

## Learning and Repeating

The [practice contract](../app-practice/app-practice.md#screens-and-practice)
owns Learning/Repeating behavior and the difference between the settled
planner-only/no-hints requirement and the current chosen-line/hint paths.
Architecturally, the Practice controller handles move/session state; the ML
controller handles stored progress and the engine; the store owns database
transactions. Both modes append to the same `practice_events` history.

### Session and transaction boundaries

`Session` holds player/line IDs, name, prescribed moves, mode, selected side,
full-line move index and monotonic move-start time. The dictionary is keyed by
player ID, storing one session UUID and `Session` per player in this process.
The HTTP boundary accepts only UUID player strings and normalizes them to hex;
direct Python callers such as the demo use their own string IDs. These are
record selectors, not authenticated identities.

`PracticeController.lock` serializes start, side selection, move submission
and early close across players in the shared controller. Catalog and repertoire
reads do not take that session lock. This does not provide sessions across
several server processes. Starting a valid line installs a new session and
replaces the previous one; completion/early close deletes it. Sessions have
no expiry or persistence. A planner response with no due line does not open or
replace a session.

`_open_line` reads catalog moves; Learning additionally checks learnability.
`_choose_side` permits White, Black and Both for lines of at least two plies,
or only White for a one-ply line. Single-side progression includes scripted
opponent moves; Both progresses one ply. Move correctness is exact UCI equality
against that sequence, not chess-engine analysis of candidate moves.

For a submitted move, the controller computes the next index and elapsed time,
then writes a `move_attempted` event inside a write transaction. If final,
that same transaction initializes Learning progress or updates review state
and writes `session_completed`. Only after the transaction exits does it
advance/delete the in-memory session. A failed database write therefore does
not intentionally advance the session. Successful persistence followed by a
lost HTTP response has no request-id/idempotency recovery mechanism.

Learning initializes a missing `player_lines` row only: existing progress,
first learned date, last review and due date survive later Learning completions.
An unfinished session may leave attempts without a completion. The early-close
path requires a running review and at least one persisted wrong attempt;
its schedule update and completion are transactional before session deletion.
Browser saves and their resume limitations are owned by
[App & Practice](../app-practice/app-practice.md#saved-lessons-and-interrupted-sessions).

## Review scheduling

### Due-line selection

`MLController.suggest` loads only that player's `player_lines` in a write
transaction. An empty repertoire yields `learn_first`; no due row yields
`none_due`. `MLEngine.select_line` filters timestamps at or before server UTC
`now`, then chooses the smallest `(next_review_at, learned_at, line_id)`.
This orders saved due-date strings under the store's timestamp representation;
it is not a learned ranking over the full event history. A selection writes
`line_suggested` without a session ID, then the Practice controller opens the
session awaiting side. There is no log of an empty/no-due suggestion.

Direct-line review instead verifies repertoire membership, uses the opening
family side, and opens immediately, including before due time. It writes no
`line_suggested`. Earlier suggestions are recorded but never read by selection.
The browser's main Start review is the planner path; its per-line actions are
the direct path. The API surface and unresolved product choice belong to
[App & Practice](../app-practice/app-practice.md#unresolved-repeating-behavior).

### Initial card, grading and update

First Learning completion creates an unreviewed Py-FSRS card due immediately. Stability and current recall remain null until the first review. After Repeating, any wrong attempt yields Again even if corrected. Otherwise the engine subtracts its configured baseline from mean response time per distinct move: under 500 ms gives Easy, 500 through 1,800 ms gives Good, and above 1,800 ms gives Hard. The web server's baseline is zero; calibration beyond this is not implemented. The grading specification changed on 2026-11-16 to the mean time per move with intervals still to be set ([review dataset record](../review-dataset/record.md#3-the-session-grading-function)); the app keeps these boundaries until then.

The controller records elapsed server monotonic time between attempts. Browser interaction, request waiting and any idle time contribute; it is not an isolated measurement of thought. A final correct attempt, session completion and schedule update share one SQLite transaction. Early close after a recorded mistake also saves a completion and updates the schedule as Again. Other unfinished sessions do not update it.

The timer starts when side is selected (or a resumed session opens), resets
after every submitted attempt, rounds to milliseconds and clamps below at
zero. It includes response/render waiting between requests; it excludes time
before side selection and the earlier part of a resumed Learning session.
The clean-grade arithmetic is total recorded response time divided by the
number of distinct move indices, minus the configured baseline. There must
be at least one attempt. `complete_review` reads attempts ordered by event ID,
restricted to player, line and session, then updates that player's saved FSRS
state, `last_reviewed_at` and `next_review_at`.

The engine calls Py-FSRS with the saved card, grade and timestamp to update stability and due date. The web server and terminal launcher load `backend/fitted_global.csv`; these are supplied demo weights, not automatically the latest experiment weights or an accepted real-player model. [FSRS training](../fsrs-training/fsrs-training.md) owns their historical provenance. The app does not set custom learning steps or fuzzing; a scheduled due date is not a guarantee of the exact target-recall crossing. Personalization beyond each player's evolving card state remains planned.

### Weight and dependency boundary

`MLEngine.from_weights_file` requires exact ordered columns `w0` through
`w20`, one complete data row and 21 finite numeric values. It constructs
`fsrs.Scheduler(parameters=weights)` and rejects values if the dependency
adjusts them. Baseline must be finite and nonnegative. `create_backend` without
a weights file uses dependency defaults; `web.main` and the terminal launcher
explicitly supply the demo CSV. `backend/requirements.txt` permits `fsrs>=6,<7`
without a lock or exact installed-version pin.

`initial_schedule` serializes a `Card(due=now)`; `schedule_review` deserializes
the saved card, calls `Scheduler.review_card` with `Rating[grade]` and the review
timestamp, and serializes the returned card. `target_recall` is the scheduler's
`desired_retention`; memory is `card.stability` plus
`get_card_retrievability(..., current_datetime=now)`, with both values null
before initialized stability. Scheduling may use short learning/relearning
steps even when stability is expressed in days. Exact dependency defaults,
fuzzing outcomes and installed runtime versions were not executed or inspected
in this source-only pass; a precise 90% crossing cannot be inferred from due
time alone. Display semantics and snapshot freshness belong to
[App & Practice](../app-practice/app-practice.md#memory-displays-and-limits).

## Presentation demo

Run `backend\run-demo.cmd` from the repository root on Windows; [project context](../../PROJECT_CONTEXT.md#build-and-review) owns setup commands. The launcher calls the practice and ML controllers, loads the 21 weights from `backend/fitted_global.csv`, and prints grade, stability, next review time and a fresh player ID. Its default is a clean Both-side review graded Good. `--side black --grade Again` demonstrates a wrong move followed by retry. Timing is simulated and repeatable within the run.

The demo writes player events and progress to `backend/tempo_demo.sqlite`. In DB Browser for SQLite, inspect `practice_events` and `player_lines` by its printed player ID. The supplied `backend/synthetic_reviews.csv` is a separate historical export recorded as 50,400 sessions from 30 simulated agents on 140 representative lines; it was not regenerated after catalog cleaning/merges. Its count and catalog scope do not describe a newly generated run.

`demo.run_demo` chooses the first learnable line by line ID with at least two
plies, creates a fresh `demo_<12 hex characters>` player and drives the same
controllers without HTTP or browser state. `--grade` selects Again, Hard,
Good or Easy; `--side` selects White, Black or Both. The default launcher runs
Good/Both with the supplied database and weights. It overrides the controller's
clock with one UTC timestamp and a synthetic elapsed counter: 0.7 s per
Learning move, and 0.7/2.0/0.7/0.3 s per review attempt for
Again/Hard/Good/Easy. Again first submits `0000`, asserts that the index did
not advance, then submits correct moves.

The demo contains executable assertions for the learned-line suggestion,
expected grade, positive persisted stability and a future due timestamp. The
launcher first checks `import fsrs`; it uses `python -B` and propagates the
demo's exit status. These are demonstration/self-check entrypoints, not a
separate backend test suite. They were inspected, not run in this pass. They
write new practice rows to the selected SQLite database; use the project run
instructions when intentionally running them.

## Offline and runtime boundary

The web server neither generates synthetic clients nor trains weights.
`backend/synthetic_clients.py` is a standalone presentation-data CSV producer;
its database reader opens SQLite read-only and synthetic events go to the
CSV, not `practice_events`. It can use fixed demonstration lines, all catalog
lines, or the first catalog line per family. Its default scheduler disables
fuzzing, unlike the runtime's unspecified dependency setting. This historical
export is separate from the run that produced the supplied app weights.
The maintained generation/fitting/evaluation package is `ml/tempo_ml/` with
configs in `ml/configs/` and dated records in `ml/experiments/`.
[Synthetic clients](../synthetic-clients/record.md) and
[FSRS training](../fsrs-training/fsrs-training.md) own producer contracts,
methods, weight provenance and evidence; the app consumes only an explicitly
configured CSV. It does not discover newer runs, automatically import their
weights, train on live history or fit per-player parameters.

## Verification scope

This documentation pass inspected source and existing records; it ran no backend, ML, frontend or browser checks. Historical demo/integration checks and their environments are in [App & Practice validation](../app-practice/app-practice.md#validation) and [the worklog](../../worklog.md). No production deployment, authentication or live personalization is verified here.

### Source-to-topic coverage

The bounded 2026-11-15 review covered every backend Python runtime/controller/
engine/demo module and the launcher/dependency boundary at `788e060`, rather
than inferring coverage from HTTP routes alone. Data/store details were
assigned separately to Catalog & Data; offline source/test coverage belongs
to its producer/training records.

| Reviewed files / symbols | Canonical topic and newly filled gaps | Verification limit |
|---|---|---|
| `backend/web.py`: `Handler`, `main`; `frontend/vite.config.ts` | Architecture: threaded local server, shared controller, static hosting, CLI file/port requirements and fixed proxy target; App & Practice: route/error contract | Source only; no listener, deployment or request exercised |
| `backend/practice_controller.py`: `Session`, `_open_line`, `_choose_side`, `submit_move`, `abandon_review`, `create_backend` | Architecture: lock, process-local lifetime, transaction order, exact move checking, timer boundaries; App & Practice: session response, resume and feedback | No concurrency, failure injection or controller run |
| `backend/ml_controller.py`: `suggest`, `initialize_progress`, `complete_review` | Architecture: selection inputs/events, first-learning idempotence, session-attempt filtering and card update | No database state mutation or runtime query |
| `backend/ml_engine.py`: `from_weights_file`, `select_line`, `grade_session`, `initial_schedule`, `memory`, `schedule_review`; `backend/requirements.txt` | Architecture: weights parser, grade boundaries, defaults/version limits, saved-card lifecycle | Dependency installation/defaults and numerical scheduling not inspected or run |
| `backend/demo.py`, `backend/run-demo.cmd` | Architecture: direct-controller entrypoint, synthetic clocks, side/grade options, assertions and writes | Assertions read, not executed; no standalone backend test files found by tracked file inventory |
| `backend/store.py`, `backend/tempo_demo.sqlite` | Catalog & Data owns schema, catalog upgrade preservation, timestamps, transaction/connection implementation and artifact identities; runtime call sites reviewed here | Separate assigned audit; not claimed as independently verified in this record |
| `backend/synthetic_clients.py` (runtime boundary/read-only reader); `backend/synthetic_reviews.csv`, `backend/fitted_global.csv` | Producer/training records own generation and historical artifact provenance; Architecture distinguishes supplied inputs from live fitting | Boundary source inspected; CSV values/row counts not remeasured here |

Checks actually executed here were file inventory, focused source/record reads,
read-only Git branch/status/source-identity inspection, and record link/diff
checks. No tests, application builds, servers, demos, training or benchmarks
were run. Inference is marked where failure or integration behavior follows
control flow without an executed case. Runtime and accepted product choices
remain distinct.

## Standalone architecture HTML

`docs/topics/system-architecture/system-architecture.html` duplicates the
generated architecture page and also supplies the figure's inline SVG source
and extraction recipe. Options: retire the standalone page after moving the
drawing source and checking consumers, or retain its synchronization duty.
Recommend retirement only after the owner approves those exact changes;
the figure source and existing route must remain available until then.

## Human overview and figure sources

The architecture overview keeps component/deployment and runtime/offline
boundaries. The App & Practice page owns the reader-facing practice journey
and practical walkthrough; canonical source records remain separate. The
requested presentation cleanup removes the former text-tile slide faces;
`components`, `practice`, `live-demo` and `architecture-diagram` anchors stay.
The standalone HTML and generated component SVG are unchanged.

The new source-authored HTML runtime flow in `index.md` is its own generator.
Its inputs are `backend/ml_controller.py`, `backend/ml_engine.py` and
`backend/practice_controller.py` at `dab04ac`: repertoire selection, attempt
grading and FSRS card update, with the final attempt/completion/schedule
transaction. The runtime/offline comparison is based on those sources,
`backend/web.py` and `ml/tempo_ml/`. The page does not claim a fresh app run.
Numeric ledger: loopback port 8000 belongs to backend web configuration;
the retained grade boundaries of 500 and 1,800 ms and zero web baseline are
configuration rules in Review scheduling above, not measured human cutoffs.
