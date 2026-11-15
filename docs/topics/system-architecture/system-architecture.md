# TEMPO system architecture

This record describes the local implementation at `5d6b81c`, inspected on 2026-11-15, and separates it from proposed deployment and planner behavior. Learning and Repeating use a Python backend and a shared SQLite practice history. [Project context](../../PROJECT_CONTEXT.md) owns terminology and settled requirements; [frontend application](../frontend/frontend.md) owns browser routes, HTTP contracts and the unresolved Repeating deviations.

## Components and deployment

The [architecture diagram](component-flow.mmd) connects the browser, practice backend, SQLite and offline training. The current local web server binds HTTP to `127.0.0.1:8000`; Vite proxies `/api` from development/preview, or the Python server serves built `frontend/dist`. These mechanisms are implemented in `backend/web.py` and `frontend/vite.config.ts`. Hosted HTTPS and persistent deployment storage remain proposals, not features of the local HTTP server.

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

In **Learning**, the player chooses an opening and learnable line. The browser uses its family's side; backend/demo callers may select White, Black or Both. The Practice controller loads moves from SQLite and returns the expected Learning move. The browser shows an arrow. A matching move advances; a wrong move leaves the same position for a retry. Completion adds a new line to the repertoire. Later Learning completions preserve the existing schedule and first learned date.

The settled **Repeating** contract is planner-selected lines, no hints/arrows, and wrong moves rejected without playing out punishment. The current browser implements two deviations: direct selection of any learned line, and an expected-move arrow after the first mistake. A second mistake offers re-learning or continuing. These are documented as current behavior, not approval to replace the contract; [unresolved Repeating behavior](../frontend/frontend.md#unresolved-repeating-behavior) owns the options and recommendation.

The normal Start review action asks the ML controller for a line. With an empty repertoire it returns `learn_first`; if no line is due it returns `none_due`. Otherwise the engine picks the earliest `next_review_at`, then earliest `learned_at`, then lowest `line_id`. The controller opens it awaiting side selection; the browser supplies the family side automatically. Direct-line review bypasses this selection and does not add a `line_suggested` event.

Sessions live in one backend process and disappear at restart. Starting another replaces the player's active session. Browser-local unfinished Learning progress resumes through a new backend session; ordinary navigation away from Repeating does not grade or complete it.

## Review scheduling

First Learning completion creates an unreviewed Py-FSRS card due immediately. Stability and current recall remain null until the first review. After Repeating, any wrong attempt yields Again even if corrected. Otherwise the engine subtracts its configured baseline from mean response time per distinct move: under 500 ms gives Easy, 500 through 1,800 ms gives Good, and above 1,800 ms gives Hard. The web server's baseline is zero; calibration beyond this is not implemented.

The controller records elapsed server monotonic time between attempts. Browser interaction, request waiting and any idle time contribute; it is not an isolated measurement of thought. A final correct attempt, session completion and schedule update share one SQLite transaction. Early close after a recorded mistake also saves a completion and updates the schedule as Again. Other unfinished sessions do not update it.

The engine calls Py-FSRS with the saved card, grade and timestamp to update stability and due date. The web server and terminal launcher load `backend/fitted_global.csv`; these are supplied demo weights, not automatically the latest experiment weights or an accepted real-player model. [FSRS training](../fsrs-training/fsrs-training.md) owns their historical provenance. The app does not set custom learning steps or fuzzing; a scheduled due date is not a guarantee of the exact target-recall crossing. Personalization beyond each player's evolving card state remains planned.

## Presentation demo

Run `backend\run-demo.cmd` from the repository root on Windows; [project context](../../PROJECT_CONTEXT.md#build-and-review) owns setup commands. The launcher calls the practice and ML controllers, loads the 21 weights from `backend/fitted_global.csv`, and prints grade, stability, next review time and a fresh player ID. Its default is a clean Both-side review graded Good. `--side black --grade Again` demonstrates a wrong move followed by retry. Timing is simulated and repeatable within the run.

The demo writes player events and progress to `backend/tempo_demo.sqlite`. In DB Browser for SQLite, inspect `practice_events` and `player_lines` by its printed player ID. The supplied `backend/synthetic_reviews.csv` is a separate historical export recorded as 50,400 sessions from 30 simulated agents on 140 representative lines; it was not regenerated after catalog cleaning/merges. Its count and catalog scope do not describe a newly generated run.

## Verification scope

This documentation pass inspected source and existing records; it ran no backend, ML, frontend or browser checks. Historical demo/integration checks and their environments are in [frontend validation](../frontend/frontend.md#validation) and [the worklog](../../worklog.md). No production deployment, authentication or live personalization is verified here.
