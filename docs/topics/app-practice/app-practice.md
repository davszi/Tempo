# App & Practice

## Current Learning and Review flow

The React application in `frontend/` uses the Python HTTP API in `backend/web.py`. It loads the SQLite opening catalog and browser player's repertoire, starts Learning and Repeating sessions, submits moves, and shows the saved schedule and review history. This describes source at `788e06039dd2869b23261dd80ea8fc49367ab33c`, inspected on 2026-11-15; it does not settle product choices left open in [project context](../../PROJECT_CONTEXT.md).

The browser currently lets the player choose a review line and shows an arrow after the first review mistake. Both behaviors conflict with the settled Repeating contract. [Unresolved Repeating behavior](#unresolved-repeating-behavior) records the differences and decision needed.

## Scope and ownership

Zeel owns the React frontend. This merged record owns the app journey, browser screens and inputs, HTTP practice contract, local identity/progress and display semantics. Backend components and scheduling mechanism belong to [System Architecture](../system-architecture/system-architecture.md); catalog/store/schema/provenance belong to [Catalog & Data](../catalog-data/catalog-data.md); offline fitting belongs to [FSRS training](../fsrs-training/fsrs-training.md). Setup and run commands belong to [project context](../../PROJECT_CONTEXT.md#build-and-review). Remaining acceptance and the Repeating decision are routed through the [product backlog](../../open/product-backlog.md).

## End-to-end flow

1. The local backend reads its configured catalog and weights. The browser
   fetches catalog/repertoire for its demo UUID; opening family and learnable
   line rules come from [Catalog & Data](../catalog-data/catalog-data.md).
2. The player chooses a Learning line. Correct move responses advance the
   board; unfinished successful positions are saved locally. First completion
   adds it to the shared repertoire with its first test due at 04:00 on the
   player's next local day; the browser sends its time zone when the lesson
   starts. Until then the line can only be practised without hints, which
   leaves the schedule alone: per-line Review and Practise actions open that
   practice instead. The [first review timing record](../../open/first-review-timing.md#implemented-in-the-app)
   holds the rule, its reasons and the deferred simulator follow-up.
3. Normal Start review asks for the next due line; its saved attempts and final
   grade feed the same shared SQLite history and schedule. Direct-line review
   and revealed moves remain implemented deviations, as recorded below.
4. Repertoire/schedule screens fetch the resulting saved dates and recall
   snapshots. [System Architecture](../system-architecture/system-architecture.md#review-scheduling)
   owns selection, timing, grading and FSRS; its
   [presentation demo](../system-architecture/system-architecture.md#presentation-demo)
   drives that controller flow with simulated timing, independently of the
   browser. Offline generation/fitting is a separate pipeline, not a web action.

## Screens and practice

The implemented hash routes are `#/home` (also the empty/unknown-route fallback),
`#/learn`, `#/family/<encoded family name>`, `#/lesson`, `#/review`,
`#/repertoire`, `#/repertoire/<encoded family name>` and `#/settings` (the
account and password reset routes are listed with accounts). `App.readRoute` decodes the family argument;
there is no URL-addressable session identifier. Opening `#/lesson` after a
page reload shows Learning when no in-memory browser session exists. Hash
navigation updates the document title and scrolls to the top.

Line lengths and progress on every screen count **moves**: the player's own
moves from the side they play, not half-moves. A 7-half-move line is 4 moves
as White and 3 as Black (every half-move with Both). `playerMovesIn`,
`playerMoveCount` and `progressMoves` in `frontend/src/lib/catalog.ts` hold the
rule; the API and saved lesson progress still store half-move indices
(`total_plies`, `ply`).

- **Dashboard:** due-review actions, unfinished lessons, and a selectable 30-day schedule with overdue lines grouped into today. It displays saved due dates; it does not simulate future reviews or refitting.
- **Learning:** search by family, variation or ECO code; filter White, Black or all families; open a family to select a learnable variation. Family previews use a shortest catalog line. Only leaf lines can start Learning; [opening catalog structure](../catalog-data/catalog-data.md) owns that rule and distinguishing labels for same-name lines.
- **Lesson:** the browser automatically uses the family's side. Learning shows an arrow and move notation, accepts click, keyboard and drag interactions, offers promotion pieces, and animates the opponent's reply after a correct move. Wrong moves leave the position unchanged. Completion marks the line learned and refreshes repertoire data. Related variations are ranked by shared opening plies, then length; the next suggestion is the first unlearned line in that order.
- **Repeating:** the main Start review action asks the planner for a due line. The browser selects its family's side automatically. Per-line Review and Practise actions also start a chosen repertoire line, including one not yet due once it has had its first review. Since `42a6810`, each of the first four mistakes reveals the expected move with an arrow, and only that move is accepted until it is played; illegal moves are ignored. A fifth mistake ends the review with a prompt whose only action is Learn this line again, which closes the review as Again before starting Learning. The backend accepts early closure after any recorded mistake; the browser offers it after the fifth. The Repeating page's introduction states the four-hint limit.
- **Repertoire:** since 2026-11-17, a grid of the opening families the player has started (a learned line or an unfinished local lesson), in the Learning page's card style: the family's preview board, lines learned out of the family's learnable lines, the weakest current recall, and due, in-progress or next-test chips. Tabs filter families (all, with a due line, all learned lines fresh, with a lesson in progress); search covers family, line names and ECO; side chips filter White or Black. Families with due lines come first, then the soonest next review. Opening a family (`#/repertoire/<encoded family name>`) shows a page laid out like the Learning family page: its line list puts learned lines first (most urgent first, each with its recall bar, "% recall now" and due chip), then lessons in progress, then the family's other lines. The selected item's panel shows, for a learned line, the memory status, Review now or Practise early, Learn again, board, moves, learned/last/next review dates, memory strength and review history; for a lesson, its progress with Continue and Start over; for any other line, Start learning.
- **Settings:** nine themes and six recoloured Lichess piece sets, with credits. Desktop navigation has a Settings control; mobile navigation includes Settings directly. The current shell has no mobile drawer.

The backend still accepts White, Black or Both sessions. The browser exposes no side choice: `App.startLearning` and `App.startReview` use `family_side`. This UI choice is implemented behavior, not a newly settled product rule.

## Identity and persistence

`frontend/src/lib/practiceApi.ts` creates a UUID in browser `localStorage` under `tempo-player` and sends it as `player_id` on every POST. This is a local demo identity, not authentication or an account system. Clearing it selects a new player identity; it does not delete the old player's SQLite records.

SQLite owns learned lines, move attempts, completed reviews and schedules. `tempo-lesson-progress` stores unfinished Learning positions in this browser; resuming opens a new backend session with `resume_at`. The backend validates that the position is inside the line and belongs to the selected side. Active sessions remain in backend memory: one per player per app process. Starting another session replaces the previous one; restarting the backend loses active sessions. Leaving a review through ordinary navigation does not complete or grade it.

`tempo-appearance` stores theme and piece choices; `tempo-learning-side` stores the Learning family filter. Local preferences and unfinished lessons do not synchronize across browsers. No password handling is implemented.

### Saved lessons and interrupted sessions

`LessonPage.submit` saves a Learning position only after a correct,
non-final server response. It stores `{ply, total, side, at}` by line ID,
where `at` is browser time. Starting a lesson and making only wrong attempts
does not create a save. Completion clears the save; Start over clears it
before opening the new session. Re-learning a previously learned line does
not reset its existing schedule or first learned date.

`App.startLearning` resumes only when the saved side matches the current
family side. The controller requires a nonzero saved index to be inside the
line and on the selected player's turn (any ply for Both). This validates
an index, not a replay of prior browser attempts. The new session's timer
starts afresh; the old attempts stay attached to their original session.
An invalid nonzero resume request opens/replaces the active session before
validation fails. The browser clears the save and shows “starts again”, but
its catch branch does not send a second start request or open the lesson;
the next explicit start begins from scratch.

The progress cache catches JSON parse failures and storage-write failures,
but does not validate saved object shapes. It keeps progress in memory when
a write fails. The player ID storage calls have no such fallback. Saved
lessons and preferences are keyed per browser origin, not per player ID;
replacing only `tempo-player` leaves them in that browser. No storage-event
listener synchronizes open tabs. These are inspected code boundaries, not
tested corruption or multi-tab behavior.

Lesson Back clears the browser session reference and navigates away without
calling a backend cancellation endpoint. Shell navigation also leaves the
backend session open. A later start replaces it. Completion and explicit
early review closure delete the active backend session; ordinary abandonment
keeps any attempted-move events but creates no completion or schedule update.
There is no endpoint to enumerate or recover active sessions, and no durable
review resume. Process restart loses them. Session and elapsed-time mechanics
are owned by [System Architecture](../system-architecture/system-architecture.md#session-and-transaction-boundaries).

A separate same-process return boundary follows from the inspected React
control flow: `App.tsx` retains only the initial start response, while
`LessonPage` keeps subsequent responses in its own local state. Shell
navigation unmounts that page without clearing App's starting response.
Browser Back or a hash return to `#/lesson` can therefore remount the old
starting/resumed board position and reset local mistake/hint state while the
backend is already farther through the line. A subsequent move can receive
a stale-index 400, or a closed-session 404 after completion. This is a
source-derived inference from `App.tsx`'s start callbacks/lesson branch and
`LessonPage.tsx`'s local state/submit handler, not an executed browser failure.
The explicit Lesson Back path clears the App session and is distinct from
shell/hash navigation. Correcting return synchronization is unfinished app
work; this documentation pass does not alter it.

## Board input and feedback

`ChessBoard` draws the position reconstructed by `learning.positionAt` from
the server's prescribed `played_moves`; the browser does not optimistically
play an attempted move. White is at the bottom except in Black sessions.
For Black, the server includes White's initial move automatically. Both-side
sessions start at zero and advance one ply; single-side sessions advance by
two, capped at the line end, including the opponent's reply.

- Click a piece of the side to move, then a destination square. Selecting
  another friendly piece changes the selection. Squares are labelled native
  buttons, so keyboard focus and Enter/Space can use the same click path;
  no arrow-key board-navigation system is implemented.
- Pointer dragging starts only for the current side's piece with the primary
  pointer button. Movement beyond 5 px becomes a drag, handled across the
  window; release off-board, on the source square, or pointer cancellation
  produces no attempt. A completed drag suppresses its following click.
- A pawn aimed at its promotion rank opens Queen/Rook/Bishop/Knight buttons
  before sending UCI with a suffix. Cancel clears that choice. Castling uses
  the king's from/to squares; reconstruction through `chess.js` moves the rook.
- Input is blocked while a request, Learning reply animation, promotion
  choice or second-mistake decision is pending, and after completion.

The live lesson sends coordinate UCI directly. It does not use `chess.js` to
filter attempted legal destinations, and the controller checks exact equality
with the expected UCI string rather than applying a chess legality engine.
An off-repertoire or illegal coordinate attempt is therefore simply wrong:
it records an incorrect attempt, leaves the position unchanged, clears the
selection and shakes the board. The hint does not physically prevent a wrong
attempt from being submitted.

After a correct Learning response that includes an opponent reply, the UI
shows the player's move first and waits 450 ms before showing the reply.
Repeating updates immediately. First-mistake hints and the second-mistake
choice are local lesson state; the backend returns `expected_move` after
every wrong Repeating attempt and grades from persisted attempts. Re-learning
from that choice first closes the review as Again, then requests fresh
Learning. Continuing hides further hints in that mounted lesson and brings
a prompt with only the Learn this line again button after two additional mistakes. The player only
returns to Learning by choosing to learn the line again. UI copy
such as “no hints” does not override these implemented behaviors.

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
| `POST /api/repertoire` | None | Server `now`, `target_recall`, forgetting-curve `decay`, learned lines with dates, stability, current recall and completed review history; `repertoire` |

Session responses contain status, session and line IDs, name, mode, side, available sides, move index, total plies, played moves and a Learning-only `hint`. The move index is zero-based across the full line. The browser chooses a side after a planner response before opening the board. Both-side sessions advance one ply; single-side sessions include the opponent reply automatically.

The handler returns JSON errors: 400 for missing/invalid request fields and controller validation failures, 404 for unknown routes or missing lines and sessions. Browser requests use relative `/api/` paths. Vite development and preview proxy them to `http://127.0.0.1:8000`; the Python server can also serve built `frontend/dist`. There is no HTTPS termination or authentication layer in this local server.

### Validation and failure boundaries

The handler checks `Content-Type` parsed as `application/json`, a numeric
`Content-Length` in the stated range, valid JSON, an object body and a string
UUID. There is no cookie or bearer-token identity check: knowledge of a
player UUID selects that player's records. All route matches use `self.path`
exactly; a query string or trailing slash changes the route. Unknown API GETs
and unknown POSTs return `{"error": "Unknown API endpoint"}`. Non-API GETs
delegate to Python's static-file handler; its errors need not be JSON.

| Controller condition | Response class / source message |
|---|---|
| Missing required field, wrong callable argument type, malformed JSON/UUID or rejected size/content type | 400, caught `KeyError`, `TypeError` or `ValueError`; messages come from the exception |
| Unknown line | 404, `Unknown opening line` |
| Learning a non-leaf heading | 400, `This line is extended by longer lines; learn one of those instead` |
| Direct review outside this player's repertoire | 404, `This line is not in your repertoire` |
| Session absent, replaced, completed or ID belongs to another player | 404, `Unknown or closed practice session` |
| Side unavailable for line, or choosing side twice | 400, `This line cannot be played from the selected side` / `The review is not waiting for a side` |
| Wrong/stale move index or no side yet | 400, `The move does not belong to the current position` |
| Bad nonzero resume position | 400, `The saved position does not belong to this line and side` (or a caught type error before that check) |
| Early close outside running Repeating, or without a recorded mistake | 400, `Only a running review can be closed early` / `Only a review with a mistake can be closed early` |

Field presence is stronger than field-type validation: there is no common
schema requiring integer `line_id`/`move_index` or string UCI. SQLite binding,
Python comparisons and the named controller checks govern other malformed
values. UCI values unequal to the expected string can be counted wrong rather
than rejected. Exceptions outside the handler's listed classes are not mapped
to a documented JSON error. Unsupported HTTP methods retain the base handler's
behavior. These limitations follow source inspection, not exhaustive fuzzing.

`practiceRequest` requires a JSON response content type, surfaces the server's
`error` on unsuccessful JSON responses, and gives a backend-start message for
non-JSON responses. It has no automatic retry, timeout or response-shape
validation. Catalog and repertoire loading failures show a Retry banner;
session actions show a toast. Catalog retry also refreshes repertoire. Move
requests carry the current session ID and full-line move index, so replaying
an already advanced/final request is not idempotent. A lost response can leave
the browser behind committed server state; recovery was not exercised here.

## Memory displays and limits

The repertoire endpoint computes current recall and stability from the saved Py-FSRS card. Both are null before the first review. Recall uses the FSRS-6 forgetting curve with elapsed time in fractional days (`MLEngine.memory`), because Py-FSRS's `get_card_retrievability` counts whole days and showed 100% for the first 24 hours after every review; at whole days the two agree. The endpoint also returns the curve's `decay`, and the browser recomputes each line's recall from its stability and `last_reviewed_at` (`recallNow` in `frontend/src/lib/memory.ts`) whenever its one-minute clock ticks, so rings, bars and "% recall now" stay current between requests. The browser uses scheduled `next_review_at` for due labels and calendar-day countdowns, presents UTC timestamps in the browser's local time zone, and refreshes repertoire data when memory screens open or sessions complete.

The UI calls the due-date countdown “days until forgetting.” Its implemented meaning is time until the scheduled review, not time until memory is lost. Do not claim that every due timestamp is the exact instant recall crosses the target: FSRS learning/relearning steps and scheduler settings also affect due dates. The local app passes no custom learning steps or fuzzing settings to Py-FSRS. Exact installed dependency defaults were not inspected in this audit.

The server returns `now`, but `App` uses `Date.now()` for due-state displays
and refreshes that browser clock every 60,000 ms. “Due” compares the exact due
timestamp; day labels compare local midnights. Recall colors are at/above the
returned target, within 0.1 below it, or lower. Before first review, the ring
says `new`, the bar uses a full “not tested” style and stability is not measured;
none of those are an observed 100% recall value. Review history bars show
elapsed days between learning/reviews, not historical stability measurements.

`timeline` places all overdue lines and today's later reviews in day zero,
then shows 29 further bins and a later count. Dashboard's “rest of the week”
means the next six bins, not the remaining named calendar week. Review queue
shows all due lines, the next six future date groups and a remaining count.
The timeline adds fixed 86,400,000-ms days after local midnight; daylight-saving
transitions and browser/server clock differences were not tested and are not
guaranteed calendar-correct. Its copy equating due dates with exact target
crossings overstates what those saved dates establish. Scheduling and grades
are owned by [System Architecture](../system-architecture/system-architecture.md#review-scheduling).

## Unresolved Repeating behavior

**Question:** should Repeating retain the settled requirements in [project context](../../PROJECT_CONTEXT.md#9-the-earlier-prototype), or should the merged browser behavior become an explicitly revised contract?

Verified source at `788e060` shows two deviations:

- **Line selection:** `PracticeController.start_review_line` (`backend/practice_controller.py:72–85`) and `/api/review/line` allow a player to choose a learned line. Dashboard cards, the queue, repertoire, family page and Learning completion call this path. Only the normal Start review action records a planner suggestion through `MLController.suggest`.
- **Hints:** `PracticeController.submit_move` (`backend/practice_controller.py:218–221`) returns the expected move after a wrong Repeating attempt. `LessonPage` (`frontend/src/components/LessonPage.tsx:48–49,87–99`) uses it for the first-mistake arrow and notation. The settled contract says no hints and no arrows.

Options:

- Restore the settled contract: planner selection only for Repeating and retry feedback without revealing the move. Keep line choice and arrows in Learning.
- Explicitly revise the product contract to permit chosen-line reviews and a first-mistake hint, documenting the effect on graded review telemetry.
- Keep strict planner-selected Repeating and design a separate optional guided practice flow, deciding whether its telemetry updates the same schedule.

Recommendation: restore the settled contract unless the user explicitly chooses revised behavior. No source change is made by this documentation pass. The implementation decision and any changed review acceptance checks wait on that answer; no inspected record explicitly supersedes the settled contract. The product to-do requesting direct Repeating access is also in conflict and must be resolved with it.

## Structure

### Source-to-topic coverage

The bounded 2026-11-15 inventory reviewed all 23 files under `frontend/src`
at `788e060`, plus the frontend entry/configuration/test group and prototype
boundary. The table names functional coverage and filled documentation gaps;
it does not claim executed acceptance from rendered routes or from helper
test names. Backend coverage is in
[System Architecture](../system-architecture/system-architecture.md#source-to-topic-coverage).

| Reviewed files / symbols | Owning sections and newly filled gaps | Verification limit |
|---|---|---|
| `frontend/src/main.tsx`, `frontend/index.html`, `frontend/src/App.tsx`: `readRoute`, `startLearning`, `startReview`, `refreshRepertoire` | Screens, saved lessons, time displays: React StrictMode entry, hash fallback, family side, resume failure, clock and refresh behavior | Source only; no browser startup or routing check |
| `frontend/src/components/Shell.tsx` | Screens: fixed desktop navigation, mobile bottom navigation, due badge, Settings access; shell navigation does not close backend practice | Native focus/route rendering not run |
| `frontend/src/components/DashboardPage.tsx`, `ReviewPage.tsx`, `RepertoirePage.tsx` (all in `frontend/src/components/`) | Screens/memory: current due-date schedule, overdue grouping, six future queue groups, local unfinished lessons, filters and history-gap bars | No DB/HTTP/UI consistency or timezone check |
| `frontend/src/components/LearnPage.tsx`, `FamilyPage.tsx` | Screens: family/variation/ECO search, side filter storage, shortest-line preview, full-line family detail, selected repertoire review | Catalog data/rules separately audited by Catalog & Data |
| `frontend/src/components/LessonPage.tsx`: `submit`, `wrongMove`, `complete`, `relearn`, `attemptMove`; `frontend/src/components/ChessBoard.tsx` | Board/session: exact move attempts, 450-ms Learning reply, promotion/castling, click/keyboard/pointer boundaries, first/second mistake choices, completion refresh | No integrated interaction, accessibility or network-failure run |
| `frontend/src/components/common.tsx` | Memory: date formatting, line labels, rings/bars, target color bands, direct Review/Practise actions, polite toast | No rendered gauge or screen-reader check |
| `frontend/src/components/SettingsPage.tsx`, `frontend/src/lib/appearance.ts`, `frontend/src/assets/pieces.json` | Screens/design: nine themes, six bundled recolorable piece sets, credits, validated preference defaults, cached SVG data URIs | Asset keys/consumer mechanism inspected; no visual/individual SVG fidelity audit |
| `frontend/src/lib/practiceApi.ts`, `frontend/src/lib/app.ts`, `frontend/src/lib/progress.ts` | Identity, API, saved lessons: UUID requests, context/types, local cache, error and storage limitations | No storage corruption, multi-tab or HTTP request exercised |
| `frontend/src/lib/catalog.ts`, `frontend/src/lib/learning.ts`, `frontend/src/lib/memory.ts` | Screens/board/memory: learnable grouping, same-name distinguishing SAN, closest-line ordering, reconstructed chess positions, exact due vs local-day labels and fixed-day timeline | Inspected algorithm; no fresh numerical or DST execution |
| `frontend/src/styles.css` | Screens/design: theme variables, board/drag styling, focus-visible rules, responsive breakpoints and reduced-motion stylesheet | No fresh wide/narrow overflow or contrast review |
| `frontend/src/data/openings.ts`, `frontend/src/lib/variations.ts`; `frontend/tests/learning.test.mjs`, `variations.test.mjs`, `memory.test.mjs` (all in `frontend/tests/`) | Validation: three old sample openings/local White-only demo, historical continuation grouping; 12 helper tests cover sample/castling/retry, labels, due bands/timeline and current catalog ranking | Tests read, not run; old local demo/grouping is not the live backend lesson |
| `frontend/vite.config.ts`, `frontend/package.json`, `frontend/package-lock.json`, `frontend/tsconfig.json`, `frontend/.gitignore` | Structure/setup boundary: proxy/plugins, commands/dependencies, strict no-emit TypeScript, ignored build/install output | Config read; lock is dependency support, no dependency install or app build |
| `prototype/tempo.html` | Design source: standalone historical browser-local trainer with embedded catalog, weights and scheduling; not the current React/API entrypoint | Header/scheduling/storage boundary inspected; no full prototype behavior qualification |

The stack is React 19, TypeScript, Vite 8, Tailwind CSS 4, Lucide and `chess.js` 1.4.0. The lockfile owns exact dependency resolutions.

The app stylesheet imports DM Sans and Manrope from Google Fonts, with system
fallbacks; piece drawings are bundled JSON rendered as SVG data URIs.
At 860 px or below, the sidebar becomes five-item bottom navigation; session,
family/detail and appearance layouts collapse at 1,100 px. At 640 px,
additional detail/action layouts stack. A reduced-motion media rule disables
CSS animation/transitions, but source inspection alone does not establish
keyboard completeness, contrast, overflow or all motion behavior.

## Design source

The initial dashboard adapted the user-supplied `Tempo - Chess Learning.zip`, from Figma file `RuaZoTR5SPWuefaVP1TYHO`, Code Layer `2:3`, preserving its colors, typography and icon/card structure. The export's authentication photograph, browser password/account implementation and Figma-specific scripts were excluded. The later rebuild at `c12eb50` uses `prototype/tempo.html` as its design source and connects the screens to the backend. These historical sources do not establish current pixel-level fidelity to Figma.

The checked-in single-file prototype identifies its own browser-only
`tempo-prototype-v1` store, embedded fitted weights and scheduling code. Its
header's family count belongs to that prototype snapshot, not the current
catalog. The React entrypoint loads `src/App.tsx` through `src/main.tsx`;
the Python handler serves `frontend/dist`. Neither path loads the prototype.
Prototype-specific scheduling, calibration and local persistence therefore
do not establish current runtime behavior.

## Validation

The 2026-11-15 audit compared source at `788e060` with these records. Executed
checks were file inventories, focused source/record inspection, read-only
branch/status/source-identity checks, and record link/diff checks. It ran no
app tests, builds, servers or browser sessions. Runtime behavior and visual
rendering were not reverified. Failure-path implications above follow source
control flow, not executed malformed-input, storage or concurrency tests.

Historical checks remain in [the worklog](../../worklog.md):

- The 2026-11-11 installation was initially blocked by Windows Controlled Folder Access; after the user allowed Node, dependencies installed and the build passed. Dashboard/navigation review included desktop/mobile, Escape/focus behavior in the then-existing drawer, no observed overflow and no console errors. Those drawer checks do not describe the current shell.
- The 2026-11-12 sample Learning demo passed three tests and a build, with browser checks of a White-side Ruy López lesson, local bookmarks and keyboard use. Dashboard simplification and sizing checks also predate the current schedule/repertoire screens.
- The 2026-11-13 catalog integration on Node.js 26.13.1 passed four tests and a build. The then-current Learning list showed 1,889 learnable lines and distinguishing labels without observed console errors.
- The `c12eb50` rebuild entry records controller checks on a database copy, all three terminal-demo sides, 12 frontend tests, a build and browser checks at 1440 by 900 and 375 by 812. These covered Black-side Learning, review mistakes/Again, re-learning, saved-lesson resume, drag interaction and theme changes, with no observed console errors or horizontal overflow.
- The `5d6b81c` merge entry records `npm ci` with zero reported vulnerabilities, 12 tests and a successful build on Node.js 24.13.0. Backend, ML, documentation and browser checks were not rerun for the merge.

`npm test` currently selects three files with 12 pure helper/sample tests. The older variation tests exercise `lib/variations.ts`; the current lesson uses `closestLines` in `lib/catalog.ts`. That suite alone does not verify the HTTP interface, browser persistence or integrated review behavior.

## Human overview and figure sources

The requested App & Practice human page consolidates the former browser and
whole-flow overview under this record; its published `whole-flow.html` slug
is retained while the source topic becomes `app-practice`. The existing
`catalog`, `learning-to-schedule` and `present-and-inspect` page anchors remain
reader entrypoints. Architecture owns components/deployment/schedule mechanics;
Catalog & Data owns catalog preparation and provenance; offline training has
its own records. The reader page can explain the complete app journey without
copying their full specifications.

The earlier overview's source-authored HTML diagrams are their own generators.
Its practice sequence used `backend/practice_controller.py`,
`backend/ml_controller.py` and `frontend/src/App.tsx` at `dab04ac`; its storage
boundary used `frontend/src/lib/practiceApi.ts`, `progress.ts`, `appearance.ts`,
the controller and schema record. These are historical source pins, not fresh
runtime measurements. The current record's audited source pin is `788e060`.
The storage figure must distinguish browser-local unfinished Learning,
process-local active sessions and durable SQLite progress.

Numeric ledger: 30 days is the implemented display horizon, 450 ms is a UI
delay, 5 px is a drag threshold, and 60,000 ms is the browser clock refresh.
They are source constants, not measured latency or recall accuracy. Local
ports 8000/5173 and startup commands are configuration owned by project context.
Historical experiments and app checks retain their original dates and scopes.
