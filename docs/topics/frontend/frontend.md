# Frontend application

## Current Learning and Review flow

The React application in `frontend/` uses the Python HTTP API in `backend/web.py`. It loads the SQLite opening catalog and browser player's repertoire, starts Learning and Repeating sessions, submits moves, and shows the saved schedule and review history. This describes source at `5d6b81c`, inspected on 2026-11-15; it does not settle product choices left open in [project context](../../PROJECT_CONTEXT.md).

The browser currently lets the player choose a review line and shows an arrow after the first review mistake. Both behaviors conflict with the settled Repeating contract. [Unresolved Repeating behavior](#unresolved-repeating-behavior) records the differences and decision needed.

## Scope and ownership

Zeel owns the React frontend. The app presents a dashboard, opening families and variations, guided lessons, a review queue, a repertoire and appearance settings. Backend, database and ML mechanisms have their own [architecture](../system-architecture/system-architecture.md), [schema](../database-schema/database-schema.md) and [training](../fsrs-training/fsrs-training.md) records. Setup and run commands belong to [project context](../../PROJECT_CONTEXT.md#build-and-review).

## Screens and practice

- **Dashboard:** due-review actions, unfinished lessons, and a selectable 30-day schedule with overdue lines grouped into today. It displays saved due dates; it does not simulate future reviews or refitting.
- **Learning:** search by family, variation or ECO code; filter White, Black or all families; open a family to select a learnable variation. Family previews use a shortest catalog line. Only leaf lines can start Learning; [opening catalog structure](../opening-catalog/opening-catalog.md) owns that rule and distinguishing labels for same-name lines.
- **Lesson:** the browser automatically uses the family's side. Learning shows an arrow and move notation, accepts click, keyboard and drag interactions, offers promotion pieces, and animates the opponent's reply after a correct move. Wrong moves leave the position unchanged. Completion marks the line learned and refreshes repertoire data. Related variations are ranked by shared opening plies, then length; the next suggestion is the first unlearned line in that order.
- **Repeating:** the main Start review action asks the planner for a due line. The browser selects its family's side automatically. Per-line Review and Practise actions also start a chosen repertoire line, including one not yet due. A first mistake reveals the expected move with an arrow until a correct retry. A second mistake in the session offers re-learning or continuing; continuing disables further hints. Choosing re-learning closes the review as Again before starting Learning. The backend accepts early closure after any recorded mistake; the browser offers it after the second.
- **Repertoire:** learned lines and unfinished local lessons, search and side filters, due/fresh/learning tabs, moves, dates, recall, stability and completed review grades. Unstarted lines are browsed through Learning.
- **Settings:** nine themes and six recoloured Lichess piece sets, with credits. Desktop navigation has a Settings control; mobile navigation includes Settings directly. The current shell has no mobile drawer.

The backend still accepts White, Black or Both sessions. The browser exposes no side choice: `App.startLearning` and `App.startReview` use `family_side`. This UI choice is implemented behavior, not a newly settled product rule.

## Identity and persistence

`frontend/src/lib/practiceApi.ts` creates a UUID in browser `localStorage` under `tempo-player` and sends it as `player_id` on every POST. This is a local demo identity, not authentication or an account system. Clearing it selects a new player identity; it does not delete the old player's SQLite records.

SQLite owns learned lines, move attempts, completed reviews and schedules. `tempo-lesson-progress` stores unfinished Learning positions in this browser; resuming opens a new backend session with `resume_at`. The backend validates that the position is inside the line and belongs to the selected side. Active sessions remain in backend memory: one per player per app process. Starting another session replaces the previous one; restarting the backend loses active sessions. Leaving a review through ordinary navigation does not complete or grade it.

`tempo-appearance` stores theme and piece choices; `tempo-learning-side` stores the Learning family filter. Local preferences and unfinished lessons do not synchronize across browsers. No password handling is implemented.

## HTTP interface

`backend/web.py:30–69` owns dispatch and request validation; `frontend/src/lib/practiceApi.ts` owns browser requests and response types. All POSTs require a JSON object with a UUID `player_id`; the server normalizes it to hexadecimal. The body must contain 1 to 4,096 bytes. Additional required fields are listed below; unlisted request fields are ignored.

| Method and path | Additional fields | Result and owner |
|---|---|---|
| `GET /api/lines` | None; no player ID | Catalog metadata and `learnable`, without moves or player progress; `Store.list_lines` |
| `POST /api/catalog` | None | Every catalog line, moves, parent, family side, `learnable` and player `learned`; `Store.learning_catalog` |
| `POST /api/learning` | `line_id`, `side`; optional `resume_at` | New Learning session; `PracticeController.start_learning` |
| `POST /api/review` | None | Planner-selected session awaiting side, or `learn_first` / `none_due`; `start_repeating` |
| `POST /api/review/side` | `session_id`, `side` | Select White, Black or Both for a waiting review; `choose_review_side` |
| `POST /api/review/line` | `line_id` | Chosen learned-line review from family side; `start_review_line`; see the unresolved deviation below |
| `POST /api/review/abandon` | `session_id` | Close a running review with a recorded mistake, save Again and reschedule; `abandon_review` |
| `POST /api/move` | `session_id`, `move_index`, `move_uci` | Correctness and updated session; completion may include `fsrs_rating`; a wrong review move includes `expected_move`; `submit_move` |
| `POST /api/repertoire` | None | Server `now`, `target_recall`, learned lines with dates, stability, current recall and completed review history; `repertoire` |

Session responses contain status, session and line IDs, name, mode, side, available sides, move index, total plies, played moves and a Learning-only `hint`. The move index is zero-based across the full line. The browser chooses a side after a planner response before opening the board. Both-side sessions advance one ply; single-side sessions include the opponent reply automatically.

The handler returns JSON errors: 400 for missing/invalid request fields and controller validation failures, 404 for unknown routes or missing lines and sessions. Browser requests use relative `/api/` paths. Vite development and preview proxy them to `http://127.0.0.1:8000`; the Python server can also serve built `frontend/dist`. There is no HTTPS termination or authentication layer in this local server.

## Memory displays and limits

The repertoire endpoint computes current recall and stability from the saved Py-FSRS card. Both are null before the first review. The browser uses scheduled `next_review_at` for due labels and calendar-day countdowns, presents UTC timestamps in the browser's local time zone, and refreshes repertoire data when memory screens open or sessions complete. Due labels update against the browser clock each minute; recall percentages remain snapshots from the last request.

The UI calls the due-date countdown “days until forgetting.” Its implemented meaning is time until the scheduled review, not time until memory is lost. Do not claim that every due timestamp is the exact instant recall crosses the target: FSRS learning/relearning steps and scheduler settings also affect due dates. The local app passes no custom learning steps or fuzzing settings to Py-FSRS. Exact installed dependency defaults were not inspected in this audit.

## Unresolved Repeating behavior

**Question:** should Repeating retain the settled requirements in [project context](../../PROJECT_CONTEXT.md#9-the-earlier-prototype), or should the merged browser behavior become an explicitly revised contract?

Verified source at `5d6b81c` shows two deviations:

- **Line selection:** `PracticeController.start_review_line` (`backend/practice_controller.py:72–85`) and `/api/review/line` allow a player to choose a learned line. Dashboard cards, the queue, repertoire, family page and Learning completion call this path. Only the normal Start review action records a planner suggestion through `MLController.suggest`.
- **Hints:** `PracticeController.submit_move` (`backend/practice_controller.py:218–221`) returns the expected move after a wrong Repeating attempt. `LessonPage` (`frontend/src/components/LessonPage.tsx:48–49,87–99`) uses it for the first-mistake arrow and notation. The settled contract says no hints and no arrows.

Options:

- Restore the settled contract: planner selection only for Repeating and retry feedback without revealing the move. Keep line choice and arrows in Learning.
- Explicitly revise the product contract to permit chosen-line reviews and a first-mistake hint, documenting the effect on graded review telemetry.
- Keep strict planner-selected Repeating and design a separate optional guided practice flow, deciding whether its telemetry updates the same schedule.

Recommendation: restore the settled contract unless the user explicitly chooses revised behavior. No source change is made by this documentation pass. The implementation decision and any changed review acceptance checks wait on that answer; no inspected record explicitly supersedes the settled contract. The product to-do requesting direct Repeating access is also in conflict and must be resolved with it.

## Structure

| Path | Responsibility |
|---|---|
| `frontend/src/App.tsx` | Hash routes, catalog/repertoire loading, session start and shared state |
| `frontend/src/components/Shell.tsx` | Desktop and mobile navigation |
| `frontend/src/components/DashboardPage.tsx`, `frontend/src/components/ReviewPage.tsx`, `frontend/src/components/RepertoirePage.tsx` | Schedule and player-memory screens |
| `frontend/src/components/LearnPage.tsx`, `frontend/src/components/FamilyPage.tsx`, `frontend/src/components/LessonPage.tsx`, `frontend/src/components/ChessBoard.tsx` | Opening selection, practice UI and board |
| `frontend/src/components/SettingsPage.tsx`, `frontend/src/lib/appearance.ts`, `frontend/src/assets/pieces.json` | Appearance and bundled pieces |
| `frontend/src/lib/practiceApi.ts`, `frontend/src/lib/app.ts`, `frontend/src/lib/progress.ts` | API requests/types, shared context and unfinished lessons |
| `frontend/src/lib/catalog.ts`, `frontend/src/lib/learning.ts`, `frontend/src/lib/memory.ts` | Catalog grouping/labels, chess positions, due labels and timeline |
| `frontend/src/styles.css` | App styling, themes and responsive layout |
| `frontend/tests/learning.test.mjs`, `frontend/tests/variations.test.mjs`, `frontend/tests/memory.test.mjs` | Pure helper and sample-line checks |
| `frontend/src/data/openings.ts`, `frontend/src/lib/variations.ts` | Earlier fixtures/helpers retained for tests; not current screen data |
| `frontend/vite.config.ts`, `frontend/package.json`, `frontend/package-lock.json` | Proxy, commands and dependencies |

The stack is React 19, TypeScript, Vite 8, Tailwind CSS 4, Lucide and `chess.js` 1.4.0. The lockfile owns exact dependency resolutions.

## Design source

The initial dashboard adapted the user-supplied `Tempo - Chess Learning.zip`, from Figma file `RuaZoTR5SPWuefaVP1TYHO`, Code Layer `2:3`, preserving its colors, typography and icon/card structure. The export's authentication photograph, browser password/account implementation and Figma-specific scripts were excluded. The later rebuild at `c12eb50` uses `prototype/tempo.html` as its design source and connects the screens to the backend. These historical sources do not establish current pixel-level fidelity to Figma.

## Validation

The 2026-11-15 audit compared source at `5d6b81c` with these records. It ran no app tests, builds, servers or browser sessions. Runtime behavior and visual rendering were not reverified in this documentation pass.

Historical checks remain in [the worklog](../../worklog.md):

- The 2026-11-11 installation was initially blocked by Windows Controlled Folder Access; after the user allowed Node, dependencies installed and the build passed. Dashboard/navigation review included desktop/mobile, Escape/focus behavior in the then-existing drawer, no observed overflow and no console errors. Those drawer checks do not describe the current shell.
- The 2026-11-12 sample Learning demo passed three tests and a build, with browser checks of a White-side Ruy López lesson, local bookmarks and keyboard use. Dashboard simplification and sizing checks also predate the current schedule/repertoire screens.
- The 2026-11-13 catalog integration on Node.js 26.13.1 passed four tests and a build. The then-current Learning list showed 1,889 learnable lines and distinguishing labels without observed console errors.
- The `c12eb50` rebuild entry records controller checks on a database copy, all three terminal-demo sides, 12 frontend tests, a build and browser checks at 1440 by 900 and 375 by 812. These covered Black-side Learning, review mistakes/Again, re-learning, saved-lesson resume, drag interaction and theme changes, with no observed console errors or horizontal overflow.
- The `5d6b81c` merge entry records `npm ci` with zero reported vulnerabilities, 12 tests and a successful build on Node.js 24.13.0. Backend, ML, documentation and browser checks were not rerun for the merge.

`npm test` currently selects three files with 12 pure helper/sample tests. The older variation tests exercise `lib/variations.ts`; the current lesson uses `closestLines` in `lib/catalog.ts`. That suite alone does not verify the HTTP interface, browser persistence or integrated review behavior.
