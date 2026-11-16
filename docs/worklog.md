# Worklog

Append-only chronology, newest entries first. Keep detailed evidence in its producing experiment or topic.

## 2026-11-16 Add accounts: create account, sign in and Google sign-in

Added player accounts. `backend/auth.py` stores users (`users`) and sign-in sessions (`auth_sessions`, created at start-up next to the practice tables). Passwords are stored only as salted scrypt hashes and session tokens only as SHA-256 hashes; the browser holds the token in an HttpOnly, SameSite=Lax cookie for 30 days. `web.py` adds `GET /api/auth/me` and `POST /api/auth/register`, `/login`, `/google` and `/logout`. A signed-in player always practises as their account, whatever `player_id` the page sends; a signed-out request that uses a registered account's ID is refused with 401. A new account always starts empty: progress made as a guest stays with the guest, whose ID the browser keeps aside while signed in and restores on sign-out. Guests can still use the app without an account.

Google sign-in uses Google's own button and checks the returned ID token with Google's tokeninfo endpoint (audience, issuer, verified email, expiry). It is off until the backend gets an OAuth client ID through `--google-client-id` or `TEMPO_GOOGLE_CLIENT_ID`; until then the button explains that it is not set up. A Google sign-in links to an existing account with the same verified email. Password reset by email is not built.

The frontend adds `#/login` and `#/signup` (`AuthPage.tsx`): one centred card in the current theme's colours, with no background image. Create account asks for the password twice. The sidebar shows the account or a Sign in button, and Settings shows the same box on phones.

Checks: 11 new backend tests in `backend/tests/test_accounts.py` (19 backend tests pass with the grading tests); frontend tests, type check and build pass. In the browser on a clean database: a guest created an account (mismatched passwords were refused); signing out returned to Sign in, a wrong password was refused, signing in again worked, the account's data was refused to a signed-out request, the Google button explained it is not set up, and the phone layout had no horizontal overflow. The commit hash is assigned by this entry's landing commit.

## 2026-11-16 Implement the session grading rule in the app

Implemented section 5.3 of the [session grading record](topics/session-grading/session-grading.md) on `feature/frontend-learning`: a Repeating review is graded from its mistakes and the browser-measured time of its timed moves, with no baseline. `LessonPage.tsx` starts a clock when the player's position is ready and sends each attempt's time with the move (`response_time_ms`). `practice_controller.py` stores that time, or the server's own interval for older clients, and rejects values outside 0 to 3,600,000 ms. `ml_engine.py` grades the first attempt of each move with the record's mistake limits, time bands and 20 s cap, and returns the breakdown with the completed review. Abandoning a review to relearn it is still graded Again, now forced rather than derived. The relearn prompts are unchanged: a choice after 2 wrong attempts, relearning only after 4.

Checks: the record's 14 test vectors and the timing edge cases pass in `backend/tests/test_session_grading.py` (8 tests); the frontend passes 15 tests, the type check and the build; scripted checks cover the abandon path and client times on a copy of the demo database. In the browser, on a copy of the presentation database, a review played at human pace was graded Good with its explanation shown, and two and four wrong attempts gave the choice and relearn-only prompts. Open question: relearning a line that another line extends fails, because the catalog only lets longer lines be learned; the review itself is saved as Again. The simulator follows the same rule (section 5.1): `ml/tempo_ml/simulator/grading.py` grades from each move's first attempt with the same limits, bands and cap, a review is a lapse only when it is graded Again, and `ml/tests/test_simulator.py` checks the 14 vectors (46 ML tests pass). The FSRS label docstring now says a pass means "not Again". Not done: the truth columns, regenerated datasets and retrained weights (sections 5.2 and 5.4), and the memory update for passed reviews with mistakes (section 6.1). If a completed review arrives without a grading breakdown, the result screen now states the grade instead of the relearn sentence. The commit hash is assigned by this entry's landing commit.

## 2026-11-16 Explain the per-move training targets on a Move recall page

At the ML owner's request, [training approaches](topics/move-recall/approaches.md)
gains section 7, where the pass chance enters each per-move arm (training,
scheduling, evaluation) with one worked pass chance (`p_pass(0.9, 6) =
0.886`), and section 8, the comparison with the 2026-11-13 arms A2 and B2
and the target one 6-move review with one mistake gives each arm. A new
Move recall page explains the move recall record and these sections; the
reading index, navigation and project context list it. No code, data,
weights or app behavior changed. Commit hash assigned by its landing
commit.

## 2026-11-16 Record the move recall decisions in their own topic

Decided on 2026-11-16 by the ML owner and recorded as a new topic at their
request: the [move recall record](topics/move-recall/move-recall.md) and
[training approaches](topics/move-recall/approaches.md). FSRS memory is the
only hidden memory model (multiplicative memory to be removed); FSRS recall
means one player move; a line is due when its pass chance under the
session grading rule, `p_pass(R, M)`, falls to 0.9, i.e. at a fixed
per-move target `R*(M)`; four arms are to be retrained on the cluster: A1
and A1c on line-level pass/fail, A1c-acc on accuracy and A1c-pass on
pass/fail through `p_pass`; true days follow the 0.9 pass chance. The
record answers the unresolved choice of the move/line recall proposal. Its
numbers are design arithmetic under independent moves (C = 0.5, S = 10
days), reproduced by a retained script (Python 3.13.3, numpy 2.5.4, scipy
1.18.1): one FSRS curve fitted to new-rule pass chances of 3, 6, 10 and 14
moves misses by up to 0.136, FSRS recall followed by `p_pass` by 0; one
review's mistake count carries 1.03–48 times the information of its pass
bit. No code, data, weights or app behavior changed. Commit hash assigned
by its landing commit.

## 2026-11-16 Decide the session grading rule in its own topic

Decided in the 2026-11-16 grading discussion and recorded as a new topic at
the project's request: the [session grading record](topics/session-grading/session-grading.md)
specifies the rule, its rationale, test vectors, implementation targets,
open items and validation plan. Rule: mistakes are moves wrong on the first
attempt; the mistake limit is 0 for lines of 3 moves, 1 for 4–7, 2 for
8–12 and 3 for 13 or more; above the limit is Again, at the limit Hard,
below it Good (Easy only without mistakes). Time is the mean of
browser-measured times of first-try correct moves without the line's first
move, each capped at 20000 ms, without a baseline; bands Fast < 1500 ms,
Normal to 3500 ms, Slow to 8000 ms, Very slow above. Without mistakes, Slow
stays Good and Very slow gives Hard; with mistakes below the limit, Slow or
Very slow gives Hard. The time values are starting values from published
orders of magnitude, not calibrated. The app's relearn prompts stay. The
record's evidence measures catalog line lengths (2,719 lines, 3–18 player
moves, 49.2% at 5 or fewer) with a retained script and gives binomial
design arithmetic comparing four mistake rules and two Good rules. Review
dataset section 3 now points to the new record and keeps the export's
grading inputs, the earlier rule and the pre-decision evidence (its 800 /
2100 ms candidate marked superseded); System architecture, Synthetic
players' ownership table, Open work, the reading index and project context
follow; a new Session grading page joins the navigation. No code, app or
data changed; the simulator and the app keep the earlier rule until the
record's implementation targets land. Documentation build, freshness check,
reader check and strict lint pass with kit 5.0.0 (Python 3.13.5, run with
`PYTHONUTF8=1` on Windows; 99 formulas compile); both changed pages were
reviewed in the browser at desktop and phone widths. Print, no-JavaScript,
reduced-motion and keyboard checks were not run. The commit hash is
assigned by this entry's landing commit.

## 2026-11-16 Grade from accuracy and total time

Decided at the project's request: the grading function takes two inputs,
the session's accuracy (share of moves right on the first attempt) and its
total time as mean time per move; one wrong move no longer gives Again by
itself, and the player finishes the line as before. Updated section 3 of
the [review dataset record](topics/review-dataset/record.md): both
decisions with rationale, the open choices (accuracy boundary for Again,
whether mistakes cap the grade, time boundaries, counting mistakes versus
accuracy), a non-decided starting structure, the deliberate implementation
lag, and consequences for training's pass label, the hidden truth and both
memory models. Section 3.5 adds accuracy evidence from the 2026-11-13 run's
123,891 Repeating sessions: 38.4% had a mistake, and one mistake leaves a
median accuracy from 0.67 on 2–3 move lines to 0.91 on 10 or more. The
Review data and grading chapter is restructured from it; the Open route
and the System architecture note follow. No code, app or data changed.
Documentation build, freshness check and strict lint pass with kit 5.0.0.
The commit hash is assigned by this entry's landing commit.

## 2026-11-16 Worked example of the two hidden memory models

Requested to explain the multiplicative versus FSRS hidden memory difference
with an example. Added a worked example to section 7 of the
[synthetic-client record](topics/synthetic-clients/record.md): one review of
a 6-move line (C = 0.5, S = 4 days) under both rules, for Good, Hard and
Easy, a high-difficulty line, a late review, a mistake and a strong line,
plus the first-exposure states. Numbers come from the package's own update
functions with FSRS-6 default weights, computed on 2026-11-16; they are not a
simulation result. The Synthetic players page gains the subsection
"Example: the same review under both rules". No code, data or result
changed. Documentation build, freshness check and strict lint pass with kit
5.0.0. The commit hash is assigned by this entry's landing commit.

## 2026-11-16 Grade by mean time per move; intervals open

Decided at the project's request: a clean session is graded by its mean time
per move alone. The earlier baseline subtraction and its hesitation
thresholds are removed from the specification, because the app cannot know
a real player's baseline. Rewrote section 3 of the
[review dataset record](topics/review-dataset/record.md) with the decision,
rationale, the open Easy/Good/Hard intervals and the deliberate
implementation lag (simulator and app keep the earlier rule until the
intervals are set). Section 3.5 records a synthetic check on the 76,287
clean sessions of the 2026-11-13 run: keeping the earlier boundaries on the
mean time per move gives 5.8% Easy instead of 31.5%; a candidate 800 / 2100
ms keeps the mix close (35.3% Easy) and changes 6.5% of clean grades. The
Review data and grading chapter is restructured from it; System
architecture notes that the app keeps its boundaries for now; an Open route
tracks the intervals. No code, app or data changed. Documentation build,
freshness check and strict lint pass with kit 5.0.0. The commit hash is
assigned by this entry's landing commit.

## 2026-11-16 Show the trait values the synthetic clients use

Requested to show baseline_ms and the concrete parameter values the
simulated players use. Extended section 3.3 of the
[review dataset record](topics/review-dataset/record.md) with each trait's
meaning, profile means, configured spread, allowed range, and the minimum
and maximum over the 300 clients of the 2026-11-13 run's `clients.csv`
(measured 2026-11-16 from the local generated file, hashes in that
experiment's dataset manifest): one α at the 0.1 limit, two β at 0. It
states that the baseline cancels in a synthetic clean grade and that the web
app grades with a zero baseline. The Review data and grading page gains the
subsection "What the simulated players actually use". No code, data or
result changed. Documentation build, freshness check and strict lint pass
with kit 5.0.0. The commit hash is assigned by this entry's landing commit.

## 2026-11-16 Explain how hesitation sets the clean-session grade

Requested to show how simulated hesitation times influence the grade. Added
section 3.3 to the [review dataset record](topics/review-dataset/record.md):
in a clean session the baseline cancels, so the graded delay is the mean
per-move hesitation 1000·H·exp(β(1−R))/(1 + α·reps); lower recall pushes
toward Hard, practice toward Easy. It adds expected delays and grades for
the three benchmark profiles at R = 1, 0.9 and 0.7 and reps 0 and 5 (formula
arithmetic at mean traits, not measurements). The Review data and grading
page's grading chapter gains a subsection and Figure 3 from it; the
calibration figure became Figure 4. No code, data or result changed.
Documentation build, freshness check and strict lint pass with kit 5.0.0.
The commit hash is assigned by this entry's landing commit.

## 2026-11-16 Explain how the two hidden memory models differ

Requested to make the multiplicative versus FSRS hidden memory difference
understandable on the site. Added "How the two updates differ" to section 7
of the [synthetic-client record](topics/synthetic-clients/record.md): what
both share, a question-by-question comparison of the stability updates read
from `memory/multiplicative.py` and `fsrs/model.py`, the multiplicative growth
factor at R = 0.9 and 0.5 (formula arithmetic), and the two studies' test
pass rates (58.2% and 38.4%) with the different catalog groupings; the cause
of the gap was not measured. Rewrote the page's hidden-memory chapter from
it and added its numbers to the record's numeric-source table. No code,
data or result changed. Documentation build, freshness check and strict
lint pass with kit 5.0.0 (lint notes about worklog links predate this
change). The commit hash is assigned by this entry's landing commit.

## 2026-11-16 Explain weight-space programming as a separate proposal

The user requested a concept-only proposal and publication. Added
[the explanation](open/weight-space-programming.md), its original mechanism
figure and an Open route. It distinguishes direct neural parameter editing
from trained parameter generation and Tempo's explicit FSRS equations. The
note cites the original report, HyperNetworks and a subsequent known-rule
study; their experiments were inspected, not reproduced. A toy ReLU example
illustrates direct weight writing without making a model-quality claim.
No implementation, model selection, training or performance experiment is
adopted. The commit identity is assigned by this entry's landing commit.

A separate Sol High review checked the terminology and cited primary sources
and found no consequential issue. The original toy-neuron assertions and SVG
XML parse passed. The first strict lint correctly rejected an unregistered
figure; automatic Reference rendering also treated SVG as text. Added its
source/input manifest entry and registered this record as a source page, then
rebuilt successfully. The public route is `html/weight-space-programming.html`.

Desktop and 390 x 844 rendering were inspected by eye; the figure's desktop
size was capped after review, with no page-wide overflow at either width.
The phone table scrolls locally. Final build/freshness, strict lint, reader
preservation, 47 existing formulas and whitespace are the publication checks.
No ML/app tests, training, paper reproduction, print/reduced-motion rerun or
shared-engine regression run is claimed for this record-only change.

## 2026-11-15 Publish the neural proposal and possible recall bug

The user explicitly requested committing and pushing the two Open notes and
their routes. This landing includes the neural FSRS proposal, its mechanism
diagram, the suspected move/line recall mismatch and the earlier draft/review
chronology below. The proposal remains unaccepted for implementation; the
bug remains unconfirmed. No source behavior, weights, dataset or experiment
result changes. The commit identity is assigned by this entry's landing commit.

Reused the unchanged proposal's independent review, desktop/phone inspection
and sparse-history probe. Final publication checks cover a fresh build,
strict lint, six-page reader preservation, all 47 existing formulas and
whitespace. Historical worklog link/title notes remain informational. No
training, app tests or shared-engine regression rerun is claimed. The earlier
entries describe the local draft state before this publication request.

## 2026-11-15 Track the possible move/line recall mismatch

At the user's request, added an Open route and
[suspected-bug record](open/recall-target-mismatch.md). It distinguishes
verified per-move generation and whole-line fitting from an unconfirmed
contract defect, records the possible intentional approximation, and names
the minimal investigation and decision needed before changing behavior.
The optimizer-start issue is left unchanged. This local documentation update
does not adopt the neural proposal or run/fix either approach.

## 2026-11-15 Save neural FSRS proposal and assess the existing approach

At the user's request, saved the unaccepted
[neural parameter-estimation proposal](open/neural-fsrs-weights.md) under Open,
with its mechanism diagram and an OPEN.md route. It separates research from
deployment, defines prefix-only inputs and matched baseline chronology, and
records unresolved execution budgets and success criteria. No training or
runtime change was authorized or made. This is a local review draft; it has
not been committed or pushed.

Reviewed the current trainer, replay/evaluation helpers and retained results
at `62ff67b`; an independent read-only review inspected simulator, experiment
and runtime differences. The proposal records strengths, target/clock
mismatches, a known better starting vector and remaining scheduling evidence.
Historical numbers were inspected rather than reproduced.

Probed sparse-history personalization → an empty result has no expected
columns and subsequent access raises AttributeError; extracted current
helpers used the actual NumPy model and pandas, without entering the
optimizer. Execution took 2.2 seconds; investigation time was not recorded.
The proposal retains the reproduction and environment. No full CLI, ML test
suite, generation, fitting or benchmark was run; SciPy/pytest/py-fsrs were
unavailable in the inspected bundled environment.

Documentation build/freshness, six-page reader preservation and strict lint
passed; all 47 existing formulas compiled. The kit still lists informational
notes for CLAUDE.md's title and retired links in historical worklog entries.
The new proposal's local generated links and anchors were checked separately.
Its Reference rendering was inspected at desktop width and 390 x 844, with
no page-wide overflow; the comparison table scrolls locally on phone. Shared
engine tests, print and reduced-motion checks were not rerun for this plain
record addition. The proposal is available in the local preview only.

## 2026-11-15 Consolidate topic ownership and audit code coverage

The user explicitly requested the actual record merges/splits, an audit of
code for missing documentation, a proper HTML explanation for every real
topic, complete applicable checks and publication. The prior menu pass had
established file rendering, not complete subject coverage. This landing
implements the accepted six-topic structure in the source records too.
The commit identity is assigned by this entry's landing commit.

### Scope and actual consolidation

Base: clean `main` at `788e06039dd2869b23261dd80ea8fc49367ab33c`.
The bounded work covered current source/configuration, related tests by
inspection, retained driver interfaces and existing evidence. It changed
documentation and links only; no runtime behavior, input data or numerical
result was authorized to change. Work stopped after every current code area
had an owning explanation, review findings were addressed, all six topic
pages were synchronized and applicable documentation checks completed.

- Frontend and whole-flow records are merged into
  [App & Practice](topics/app-practice/app-practice.md). The old two topic
  folders are gone. The merged topic owns screens, board input, identity,
  saved lessons, HTTP contract, display semantics and the player journey.
- Catalog decisions and the database schema are merged into
  [Catalog & Data](topics/catalog-data/catalog-data.md). The opening-library
  material is [historical provenance](topics/catalog-data/provenance.md)
  inside that topic. Unique field mappings, types/required values, rationale,
  queries, identities and old migration evidence are retained. The duplicated
  standalone schema HTML is retired, with its exact Git source cited there.
- [System Architecture](topics/system-architecture/system-architecture.md)
  owns runtime coordination, session/transaction boundaries, selection,
  grading, weights and the terminal demo, linking the app journey.
- Simulator policy and hidden memory implementations move from Training into
  [Synthetic Players](topics/synthetic-clients/record.md); [Review Dataset](topics/review-dataset/record.md)
  owns telemetry, sidecars, grading and future calibration. [Training](topics/fsrs-training/fsrs-training.md)
  owns replay, fitting, metrics, artifacts and scoped historical results.
- The completed retraining plan is retired. Its accepted comparison/metric
  criteria and unique motivation probe are absorbed into Training, with an
  exact pre-change Git link for the superseded protocol/task text.
- Product acceptance moves to [the open backlog](open/product-backlog.md);
  package setup moves from the nested README to [ML development](development/ml.md).
  The repository root retains the only project-authored README.

The six authored topic URLs remain stable (`whole-flow`,
`system-architecture`, `opening-catalog`, `synthetic-clients`,
`review-dataset`, `fsrs-training`). Their canonical source/Reference paths
follow the consolidated owners. The [reading index](index.md#reading-order)
and project context route those owners. No generic documentation/audit topic
or archive collection was created.

### Code-to-documentation audit and findings

The source inventory covered eight backend source/launcher files, all 23
frontend source/style/asset files plus configuration/entrypoint and three
helper test files, all 17 ML package files, four generation configurations,
four ML test files and six retained experiment Python drivers. The historical
HTML prototype was classified as a non-current design source. Root also
inspected CI/site configuration, the figure recipe and SQLite store/schema.
Topic-local coverage tables map modules/symbols to the filled explanations;
tests inspected are distinguished from checks actually executed.

New coverage includes HTTP validation/errors, coordinate move input,
resume/identity/cache isolation, clock and snapshot displays, commit/response
failure boundaries, store locking/upserts/constraints, generation policy and
random streams, hidden models, output identity/alignment/rounding, replay
masks/targets, optimizer/personalization and metric/artifact contracts.

Independent reviews compared source and predecessor records. Corrections:

- Restored catalog DDL type/nullability details in a 27-column matrix;
  limited line-ID preservation claims to the implemented operations.
- Corrected an inherited classifier deletion pin: `ea3d01d` removes it;
  `825e9d8` is the retained pre-removal source.
- Documented same-page lesson-return desynchronization as a source-derived
  inference: App retains the initial response while LessonPage advances local
  state, so a shell/hash return can show a stale position and later receive a
  stale-index/closed-session response. No app failure was executed here.
- Corrected the decay-clipping explanation: exported w20 can be clipped,
  but current hidden start/update do not read it and use trait-derived R.
  The limit concerns exported/fitted representability, not a changed hidden
  simulation. No incidence was measured.
- Documented the fresh generation-directory precondition. The generator can
  retain/hash stale CSVs, including old hidden weights. This follows source
  control flow; no historical dataset contamination is established.
- Retained study drivers expose a reversed paired-gain legend (positive
  actually favors the first-named model), an exact-clock loss mask retained
  during calendar replay, and a formatter that embeds historical constants
  and rounds despite its broader automatic/unrounded claim. Current Training
  explains these discrepancies without recomputing recorded scores.

Existing no-hints/planner-only requirements remain settled; implemented
review hints/direct selection remain unresolved deviations. Missing human
calibration, app-to-training export, current catalog importer and operational
recovery policies remain explicit limitations, routed to their owners. This
pass does not turn them into accepted requirements or implemented features.

### Verification and evidence scope

Documentation used the existing project Python 3.12.14 environment,
Mistune 3.3.4, Pygments 2.21.0 and Node 24.13.0/KaTeX 0.16.11. Full build,
freshness, strict lint, reader preservation and scoped content checks are
recorded for this source state. New topic inputs required intent-to-add
registration before the kit could build them; the first integrated build
also correctly rejected eight retired generated Reference files. Those
exact old build outputs were removed, then the complete site was rebuilt.
No shared-kit source or pin was changed.

There are six real topic folders plus Home, each with its authored entry;
all have canonical records except the reader-free Home. The tracked Markdown
coverage inventory is 28 files: seven authored entries and 21 Reference
sources, with no unmatched file. The corresponding public bundle has 28 HTML
routes. A local HTTP sweep returned 200 for all 28; the old Guide and
four sampled retired Reference routes returned 404.

A new read-only SQLite check confirmed all four field/index layouts,
82 families, 2,719 lines, 1,889 leaves and no foreign-key violations; seed
SHA-256 before/after remains
`5eb848f110d5f3634344b854038a4482a16c7d2ecc7da782b01c2b326188eaa0`.
The owning data record contains the command and limits. No Store startup,
write connection, migration, training, benchmark or app session ran.

The architecture figure recipe's current input path was updated after the
merge; the SVG remains byte-identical at
`f057fd808e6f4fc5d2c084bbca814701c819814e63395039d144966faeaf97da`.
The source HTML remains a required drawing input. `backend/store.py` changed
only its documentation-path comment; an AST comparison with the base is
identical. Frontend/ML code, weights, seed and numerical experiment outputs
are unchanged. Two historical SUMMARY files have exactly three href repairs
(plan to pinned Git source, catalog to current owner); measured prose and
results are preserved.

Worklog entries remain append-only. `worklog_links_checked_from` is set to
2026-11-16 so same-day historical entries can retain their original paths
through this consolidation. This entry's current links were checked separately;
that cutoff does not exempt current records/pages from strict lint.

Root inspected all six rendered pages in wide (1440 x 1000), phone
(390 x 844) and equal-column reading. Initial geometry checks found no
page-wide overflow, broken images or SVG labels below 11 px. The by-eye pass
found several narrow tables and clipped flow labels; ten table regions were
made locally scrollable/focusable and labels shortened, then the affected
rendering was checked again. All original source words, public anchors,
tables, media and SVG geometry remain covered by reader parity. The site
uses ordinary figures, with sequential captions and source/prose links.

Temporary copies with every script element removed exercised static reading
at both widths for all six topics: all chapter sections remained visible,
with no document overflow. These copies used identical CSS/media paths;
this was a derived no-script fixture, not a browser preference toggle.
Keyboard menu/focus, table scrolling, reader/history navigation and actual
Reference citations were checked in the normal site. Print/reduced-motion
rules were inspected in the unchanged shared CSS; native print output and
reduced-motion emulation were unavailable through this browser API and are
not claimed as executed checks. The previously recorded Windows shared-kit
suite failures remain historical limitations; no successful fresh engine
suite or application test run is claimed.

The earlier preview listener had ended. The owned generated-output server
was restarted hidden on loopback port 18321 and retained for the user;
port 8321 was not touched. A stale error-page tab required a fresh tab in the
same approved browser after the server was confirmed reachable. No browser
security settings or transport were changed.

## 2026-11-15 Curate topics and enable Reference

The user requested removal of the starter Guide, kit 5's Reference section,
a full merge/split/order pass, HTML counterparts for the topics, a local
preview and publication. They explicitly chose curated topic pages in the
main menu, with plans and experiment detail in Reference.

The [reading index](index.md#reading-order) records the six-topic order:
App & practice, System architecture, Catalog & data, Synthetic players,
Review data & grading, then FSRS training. The browser overview joins the
player journey; library provenance, catalog rules and schema share one
human overview while keeping separate canonical records. Producer model,
telemetry/grading and fitting remain distinct. Human calibration remains a
future chapter; backlog, setup, plans and results remain supporting records.
The Guide page and record were removed. No replacement documentation topic
was created. Historical worklog links to retired sections now point at their
committed versions; their historical statements are preserved.

Six curated pages plus Home are built, alongside 24 automatic Reference
pages. A tracked-Markdown inventory found 31 existing files: seven authored
entry pages and 24 Reference sources, with no missing HTML counterparts.
The 11 topic records are files, not 11 required main-menu topics. Existing
source and experiment paths, public section anchors and legacy generated
heading aliases were retained. Current overview links lead to rendered
Reference pages. The reading index links to the published overview routes
so it works as a source record as well as a Reference page.

App and ML contributors independently inspected the other side's content
against records and source at `dab04ac`. Missing legacy heading aliases and
one baseline-provenance omission were corrected before landing. Canonical
records received figure and number provenance before the new overview
material. The catalog tree uses verified seed rows, not an invented example.
Current app deviations and synthetic-only limitations remain explicit;
this presentation change grants no new product or experiment acceptance.

Executed documentation checks in the existing Python 3.12.14 project
environment, with Node 24.13.0 for KaTeX:

- Full build, non-mutating freshness and strict lint passed. All 47 formulas
  on three pages compile. Lint reports zero warnings; the existing automatic
  `CLAUDE.md` page has an informational filename-title fallback note.
- Reader parity passed on all six reader pages, preserving words, code,
  links, media, public anchors, folds, tables and SVG geometry.
- All 31 public HTML routes returned HTTP 200 from the owned local preview
  server; the retired Guide route returned 404.
- All six overviews were inspected in wide (1440 x 1000), phone (390 x 844)
  and equal-column reader layouts. Browser measurements found no document
  overflow or broken images. Architecture/schema drawings use labelled
  local scrolling to retain legible labels. Narrow training tables now
  scroll locally with focusable labelled regions. Keyboard scrolling was
  exercised, and Escape closed the phone menu and returned focus to its
  opener. A training citation opened its actual Reference page and fragment.
- The by-eye pass found cramped technical table names and clipped flow
  labels; those were corrected. Intermediate table wrappers swallowed
  adjacent Markdown, and a Windows default-encoding read damaged punctuation;
  both were caught in rendering and corrected using explicit UTF-8 and blank
  block boundaries. Formula, link and rendering checks were repeated after
  those corrections.
- The new diagrams replace the architecture/flow text-tile slide faces;
  their prior open design choice is resolved by this ordinary-figure layout.

No app, training or benchmark run was required or executed. App source,
seed data, weights, experiment artifacts and the kit pin are unchanged.
The shared engine was not edited; its previously recorded Windows suite
failures remain historical limitations, not a fresh successful suite run.
No-JavaScript, reduced-motion and print output were not re-exercised in the
browser for this content pass. Exhaustive keyboard/touch coverage is not
claimed. The local server on loopback port 18321 is retained for the user's
preview; port 8321 belongs to another project and was left alone.

## 2026-11-15 Relocate the kit audit

At the user's request, removed `docs/topics/documentation/documentation.md`
after distributing its useful material to existing owners. Setup and
publication policy live in `docs/PROJECT_CONTEXT.md`; catalog verification
in the opening-catalog evidence; ML evidence and cleanup choices in FSRS
training; legacy HTML and slide choices in their subject records. Current
index/page/open-work links were updated. The prior audit entry's link alone
now targets its committed Git version; its historical wording and results
were preserved. No new topic or replacement audit document was created.

The following preserves the completed kit 5 audit evidence from `5e709b8`.
These are historical results, not claims that the relocation reran app or
experiment tests. The checks for this relocation are recorded before landing.

### Prior audit scope

The completed kit adoption and documentation audit started from local merge `5d6b81c` on 2026-11-15:
all project docs, six existing topic pages, site configuration, app source
and current ML code. Historical experiment records/results and old worklog
entries retain their original source scope.

Work is limited to docs and their configuration. It does not change app
behavior, catalog, inputs or weights. Checks cover documentation build, lint,
reader regression and rendered review; no training or benchmark is rerun.
A contradiction requiring a product decision is recorded, not resolved by
inventing approval. Temporary failed checks are distinguished from results.

### Prior kit and environment

| Item | Identity |
|---|---|
| Previous kit | 3.2.1, `f34cf63e769fa49a16e42f9768aa239e94dadac5` |
| Adopted kit | 5.0.0, `25c058d094160faa517ec16f72ab44ed984c87ad` |
| Migration | 4.0 content steps, then 5.0; one pin movement |
| Environment | `.build/docs-env`, created using desktop-bundled Python; project-local dependencies |
| Packages | `mistune==3.3.4`, `Pygments==2.21.0` |
| Python | 3.12.14; the plain `python` alias on this host did not work, so the project environment was created from the bundled interpreter |
| Build output | `.build/docs/`, ignored |
| Commands | [Project context](PROJECT_CONTEXT.md#documentation-website) |

The initial 3.2.1 build passed. Strict lint found 29 pre-existing `OPEN.md`
bullets without owning-document links. The first 5.0 build passed; its strict
lint also found numbers only on the Guide slide face. These baseline
findings do not establish an app regression.

### Prior audit corrections

- Current app records distinguish implemented browser/API behavior from
  proposed hosted deployment and future personalized planning.
- Storage/API descriptions separate browser identity/progress from SQLite
  history and identify the absence of account authentication.
- The settled no-hints/planner-selected Repeating contract remains; current
  deviations are recorded for a decision in the frontend topic.
- ML docs distinguish current `ml/tempo_ml/` commands from retired simulators
  and historical results. Source pins and measured limitations remain.
- Product acceptance has a subject record; `OPEN.md` holds routes instead
  of detailed, partly stale checklists.
- The router includes the new capability-map route. No dedicated reusable
  supporting-tooling tree is declared; domain app/ML source and experiment
  scripts keep their existing owners.
- Manifest-hashed SVG figures use LF checkout through `.gitattributes`, so
  Windows line-ending conversion does not silently change their byte identity.

### Prior conformance and verification

Executed after integration: full site build, freshness check, strict lint,
and `build --check-reader` pass; the latter preserves words, links, media,
anchors and SVG geometry for all five reader pages. The home page uses no
chapter reader. All 47 formulas on three pages compile with KaTeX 0.16.11.
Source inspection is not app runtime or visual validation.

A disposable fresh local clone of the committed candidate also passed the
full build, freshness, strict lint, five-page reader check and all 47 formula
compilations. Its submodule was initialized at the exact adopted pin; only
tracked project sources were available. The figure SHA-256 still matched
after Windows checkout. This reused the documented pinned documentation
environment; it is not a clean-machine dependency-install qualification.

Shared-engine checks were also executed with the generated starter fixture:
347 Python tests ran in 177.083 seconds, with 9 failures, 4 errors and 28
skips. The suite is not clean on this Windows host. Reported cases include
POSIX `/tmp` working directories, slash-format expectations, CRLF byte
comparisons, path ordering and Windows path normalization in pin/local-file
checks. The pin helper compares Git's slash-form path with a native Path;
the consumer's actual pin was therefore additionally checked with
`git -C .docs-kit branch -r --contains HEAD`, which lists `origin/main`.
No shared-kit source or test expectations were changed to hide these failures.

The failing modules/cases were `test_kit_pin` (two unpublished-pin checks),
`test_portability` (three unrelated-working-directory errors and two shared
asset byte comparisons), `test_markers` (registry path extraction),
`test_reference_listing` (route ordering), `test_site_contract` (declared
local artifact path), `test_source_links` and two `test_source_pages` cases
(slash-form link diagnostics). No rerun with altered thresholds or patched
upstream code was used. Missing optional page-lock dependencies account for
some skips; the suite's exact skip reasons remain its own test output.

The Node reader-navigation/fold/key/dialog/history/column tests and
panel-switcher logic tests pass. Math-renderer and source-file-link Node
tests pass after supplying the generated starter output at their expected
fixture path; their first invocation lacked that fixture. These fake-DOM
checks are not browser pixel inspection. Page-lock behavior was not adopted
or qualified. The passing Tempo checks do not imply the entire upstream
cross-platform suite passes.

| Conformance item | Disposition |
|---|---|
| Pin | v5.0.0 release reachable on kit remote |
| Build/lint/freshness/reader | Pass in working checkout and fresh tracked clone; 47 formulas compile; shared-suite Windows failures reported separately |
| Router | New capability-map route added; existing routes retained |
| Shared rules | Shared guides remain in kit; records contain project facts |
| Canonical homes | Context/index/topics/worklog/open routes present |
| Tooling | `tooling_roots = []`; capability map states current scope |
| Topic structure | Six existing sources; no new public topic page |
| Records/pages | Content reconciled; face design decision below |
| Open work | One-line linked routes |
| Compatibility | Existing topic routes and standalone HTML retained |
| Changed guides | Existing Guide/Home updated for kit and project |
| Rendered review | Six pages at wide/phone widths; all eight faces in-page and deck; paired diagrams checked; limits below |

### Prior rendered review

The page author reviewed the six published pages at 1440 by 1000 and 390 by
844, and the coordinator inspected the captures by eye. No document-level
horizontal overflow or broken images were observed. Latency/calibration
figures were also checked in two equal 495-pixel columns: their steps stack,
and long formulas scroll inside their own region. Phone chapter navigation
opens, Escape closes it and returns focus, Tab exposes a visible layout-control
outline, and deck Left/Right navigation works. These are focused checks, not
exhaustive accessibility or touch qualification.

Two observed rendering faults were fixed: shared CSS had overridden the
architecture SVG's region colors, and kit image inlining dropped the image's
minimum width. Original selector specificity and an opaque dark canvas now
preserve contrast; an inner labelled scroll region keeps the 970 by 422
drawing at 900 pixels wide on a phone. Its 12-pixel source labels therefore
render at approximately 11.13 pixels (design scale arithmetic). The source
HTML, definition and manifest recipe remain together, and extraction was
verified byte-identical to the SVG and its recorded SHA-256. LF checkout keeps
that identity stable across hosts.

All eight faces were inspected in their page and extracted deck at both
widths. No text cut off or parts outside the face were observed. Wide deck
faces are 1440 by 810; phone faces stack. Each still needs an owner decision
about design under the new real-visual rule:

| Face | First focus and empty-band observation | Design finding |
|---|---|---|
| `guide#pipeline` | Title, then highlighted ownership tile; broad bands above/below tiles | Tiles name owners but omit the chapter's flow arrows |
| `guide#slides` | Title, then bright 1/0 counts; broad bands around factor list | Text factors/counts repeat the chapter rather than show its mechanism |
| `system-architecture#components` | Host takeaway title, then application-host tile; broad bands around row | Deployment boxes lack the real component drawing shown below |
| `system-architecture#practice` | Shared-history title, then Learning/Repeating pair; broad bands | Labels do not show the actual state/grade transition |
| `system-architecture#live-demo` | Outcome title, then Run tile; broad bands | Run/read/inspect list is textual rather than a visual result |
| `whole-flow#catalog` | Catalog title, then catalog count tile; broad bands | Counts and labels do not show catalog structure |
| `whole-flow#learning-to-schedule` | Practice-flow title, then Learn tile; broad bands | Three labels repeat the prose without its transitions |
| `whole-flow#present-and-inspect` | Saved-review title, then PowerShell tile; broad bands | Text-only task list does not show the saved record |

The compact phone faces remain legible. The faces were not redesigned,
removed or newly created. Review-only generated decks/captures are scratch;
the observations above are the durable result.

Not executed: rendered no-JavaScript fallback, browser reduced-motion mode,
print output, exhaustive keyboard/touch checks, the shared automated browser
helper, or app runtime tests. Node tests cover some reader print/motion logic
in an imitation DOM; that does not qualify the browser output. The retained
standalone database-schema HTML received a content/source synchronization,
not a separate rendered qualification.

### Relocation checks

This cleanup passed the full documentation build, strict lint/link/anchor
checks, freshness check and five-page reader parity check; all 47 formulas
compile. The retired topic directory is absent and current internal links
no longer name it. Only the historical entry's pinned Git link remains.
Application code, catalog, weights and page layout were unchanged. App/ML
runtime tests, shared-kit regression tests and a new browser layout review
were not rerun for this content relocation; the prior results above retain
their original scope.

### Current owners of remaining choices

- [Publication and formula enforcement](PROJECT_CONTEXT.md#documentation-publication-choices).
- [ML evidence gaps](topics/fsrs-training/fsrs-training.md#historical-evidence-gaps) and [record cleanup](topics/fsrs-training/fsrs-training.md#retained-retraining-plan-and-ml-setup-guide).
- [Standalone schema HTML](topics/database-schema/database-schema.md#standalone-schema-html) and [architecture HTML](topics/system-architecture/system-architecture.md#standalone-architecture-html).
- [Guide faces](https://github.com/davszi/Tempo/blob/dab04ac60686267372bd087d9a6e591fda71b5a1/docs/topics/guide/guide.md#slide-design-review), [architecture faces](https://github.com/davszi/Tempo/blob/dab04ac60686267372bd087d9a6e591fda71b5a1/docs/topics/system-architecture/system-architecture.md#slide-design-review) and [flow faces](https://github.com/davszi/Tempo/blob/dab04ac60686267372bd087d9a6e591fda71b5a1/docs/topics/whole-flow/whole-flow.md#slide-design-review).

The commit hash is assigned by this entry's landing commit.

## 2026-11-15 — Adopt kit 5.0 and reconcile Tempo documentation

Upgraded `.docs-kit` from 3.2.1 (`f34cf63`) to 5.0.0 (`25c058d`) through the
4.0/5.0 migration steps. Preserved the six-page publication scope with
`reference_listing = false`; added the capability-map route and inventory.
Reconciled frontend/API/storage, schema, catalog, architecture, end-to-end,
synthetic-client, review-dataset and ML records with source, then synchronized
the existing pages and figure sources. Corrected catalog counts, retired
paths, timing units, historical/current claims and unsupported calibration
language. Moved the six product requests to an owning record; `OPEN.md` is
now routes only. Kept settled Repeating decisions intact and recorded the
implemented hint/selected-line deviations for the owner rather than approving
them. No app behavior, SQLite data, weights or historical experiment results
changed. Reason: the user requested kit 5.0 and an audit of all documentation.

Validation: Tempo build, freshness, strict lint and five-page reader parity
pass; all 47 formulas compile. Read-only SQLite checks confirm 2,719 lines,
82 families and 1,889 learnable variations. Independent review findings were
corrected. The shared kit's Python suite ran 347 tests with nine failures,
four errors and 28 skips on Windows; Node reader, panel, math and source-link
checks pass. Exact scope, rendered-review findings, reproduction identities
and remaining owner choices are in the
[documentation adoption record](https://github.com/davszi/Tempo/blob/5e709b82e12a9a4889187735fd90ddfa0840765d/docs/topics/documentation/documentation.md).
Existing slide faces and unapproved file retirements remain explicit follow-up,
not a claim of complete kit-design conformance. No push or publication was
performed. The commit hash is assigned by this entry's landing commit.

## Merge frontend learning into main

On 2026-11-15, merged `feature/frontend-learning` at `c12eb50` into `main` at `ea3d01d`, retaining the frontend and backend integration from the feature branch and the current ML package, FSRS-memory simulator and experiment records from main. Resolved the sole conflict in this worklog by preserving both branches' entries. Reason: land the frontend branch at the user's request. Validation on Node.js 24.13.0: `npm ci` completed with zero reported vulnerabilities; `npm test` passed all 12 tests; `npm run build` passed TypeScript checking and production bundling. Source comparison confirmed backend, frontend and prototype files match the feature branch and ML files match main. Backend, ML and documentation checks were not run because this host has no working Python installation; the prior Pages run already failed at strict lint. No browser review was performed for this merge. The commit hash is assigned by this entry's landing commit.

## Add FSRS-6 hidden memory to the package simulator and remove ml_1000bots

Added a second hidden memory model to `ml/tempo_ml/simulator/`: `memory/fsrs.py` gives each client its own 21 FSRS-6 weights (defaults with log-normal noise, sd 0.15, on w0–w16; w20 = the client's C) and updates stability and difficulty with the graded FSRS-6 rules, with the same 1-day lapse floor as the multiplicative model. It is selected with `"memory": "fsrs"` (`configs/fsrs-memory*.json`); the default stays `multiplicative`. `clients.py` gains a branch used only by graded memory models, `LineMemory` an optional `difficulty`, `practice.py` the `memory` and `fsrs_weight_noise` fields (the weights come from their own random stream), and `generate.py` writes `memory_weights.csv` for FSRS memory; `fsrs/train.py`'s `fit` accepts optional `ftol` and `gtol`. Ran arms A1 (py-fsrs), A1c and B1 of the [retraining plan](topics/fsrs-training/retraining-plan.md) on it with the A2/B2 configuration, split, trainer settings and metrics: on 60 test clients (38.4% pass) the defaults score log-loss 0.8307, A1c 0.6084 and B1 0.6091 (86% of the gap to a perfect predictor, 0.5735); B1 is 0.0008 worse than A1c; A1 scores 0.7135 on exact time and 0.6127 on calendar days, its training clock, against 0.6117 for A1c. Removed `ml/ml_1000bots/` (simulator, opening library build, `tempo_v1`, first training run; retrievable at `825e9d8`) at the user's request: the package now covers its FSRS-memory arms, and two simulators no longer need maintaining. Its unlanded exploratory work (A1/A1c/B1 on 1,000 clients, a loss benchmark, a schedule comparison, a cross-test and a re-implementation of the A2/B2 policy) was not committed; the experiment record summarises the parts that led to this run. Updated the FSRS training record, the retraining plan status, `PROJECT_CONTEXT.md`, `docs/index.md`, `ml/README.md`, the opening library and catalog records and product to-do 6 for the removal. Reason: compare the two memory models with everything else identical, in one code base. Checks: 45 tests pass (3 new: FSRS memory matches `tempo_ml.fsrs.model`, weight sampling, lapse floor); with `configs/multiplicative-memory*.json` the generator writes the same eight CSVs, byte for byte, before and after the change; a clean checkout of `825e9d8` plus exactly these changes regenerated both datasets byte for byte and reproduced all three weight files and every score exactly; Documentation build passes; lint reports the 29 existing "bullet without an owning-doc link" errors in `OPEN.md` (30 before; one of these bullets gained a link). Record: [2026-11-14-fsrs-memory](../ml/experiments/2026-11-14-fsrs-memory/SUMMARY.md). The commit hash is assigned by this entry's landing commit.

## Retrain the 300-client FSRS-6 variant on the cleaned catalog

Ran the `ml_300bots` part of the [retraining plan](topics/fsrs-training/retraining-plan.md). The generator now reads the opening catalog from `backend/tempo_demo.sqlite` (families drawn uniformly, since the catalog has no popularity column); `train.py` gained `--target {pass,true}` (log-loss on pass/fail, or MSE on the hidden `p_clean`) and `--no-personalise`; train and benchmark report RMSE(bins), RMSE and MAE against the truth, and the error in days to 90%. The whole v1 run (`experiments/fsrs-synthetic-v1/`) and its page `ml/ml_300bots/fsrs_results.html` were removed at the team's request (retrievable at `09f8a22`), and generated data is now ignored. Results on 60 test clients, RMSE against the true chance: defaults 27.7 pp, pass/fail arm A2 14.1 pp, true-recall arm B2 13.8 pp (B2 stopped at the 300-iteration limit); hold-out clients agree. Scored on the same clients, the v1 weights reach 13.1 pp, better than A2, and also a lower log-loss on A2's own fit clients, so A2's optimizer stopped in a worse local optimum; A2 stays better calibrated (2.6 vs 4.1 pp). In days, A2 and B2 schedule a median 0.14 and 0.10 days early, and 45–47 days early on lines whose true time to 90% is 30 days or more. After the run the package moved to the shared layout: `ml/ml_300bots/ml_engine/src/tempo_ml/` became `ml/tempo_ml/` with `catalog.py`, `fsrs/` (`model.py`, `train.py`), `simulator/` (`clients.py`, `memory/multiplicative.py`, `recall.py`, `practice.py`, `grading.py`, `generate.py`, which now takes `--config`) and `evaluate/` (`metrics.py`, `days.py`); generator settings in `ml/configs/multiplicative-memory*.json`; tests `ml/tests/` (simulator, memory models, trainers, metrics); generated data `ml/data/` (ignored); and the run `ml/experiments/2026-11-13-fsrs-synthetic-v2/` with `SUMMARY.md`, `results/binary/` (A2), `results/true-recall/` (B2), `dataset_MANIFEST.txt`, `code.diff` (the run used uncommitted code on `09f8a22`) and its scripts (`holdout_benchmark.py`, `compare_v1.py`, `benchmark_data.py`). `ml/ml_300bots/` and its `summary.md` were removed; `ml/ml_1000bots/` is unchanged and not yet moved. The catalog reader follows `d2e5903` and reads only `family_side`. Checks: 42 tests pass (7 new), including loading the current catalog; regenerating the data from `09f8a22` plus `code.diff` reproduced all eight CSVs byte for byte; after the reorganisation a test dataset is byte-identical and the v1 comparison and hold-out benchmark reproduce exactly; the 21 `ml_1000bots` tests still pass. Record: [2026-11-13-fsrs-synthetic-v2](../ml/experiments/2026-11-13-fsrs-synthetic-v2/SUMMARY.md). The commit hash is assigned by this entry's landing commit.

## Rebuild the frontend from the UI prototype and connect it to the backend

On 2026-11-14, on `feature/frontend-learning`, replaced the React screens in `frontend/` with the design of `prototype/tempo.html`, now driven by the backend instead of browser-only data. Screens: a dashboard with a 30-day memory timeline and the lines fading soonest (product to-do 4), Learning mode filtered by `opening_families.family_side`, an opening page with the board beside every learnable variation, guided lessons that save progress in the browser and resume where the player left, Repeating mode (no hints; the first mistake shows the expected move once, a second offers re-learning or continuing), the repertoire with recall, days until forgetting and review history (product to-dos 1 and 5), and themes with recoloured Lichess piece sets (credits shown in Settings). Every opening is learned and reviewed only from its family's side.

Backend additions, all additive: `POST /api/repertoire` returns each learned line with its schedule, FSRS stability, current recall from the scheduler and completed reviews; `POST /api/review/line` reviews one chosen repertoire line from its family's side; `POST /api/review/abandon` closes a review after a mistake, graded Again, when the player chooses to re-learn; `POST /api/learning` accepts an optional `resume_at` at a position where the player is to move; a wrong move in Repeating returns `expected_move`. "Days until you forget" is defined as `next_review_at - now`, the moment predicted recall falls to the scheduler's target.

Checks: a scripted controller run on a copy of the demo database covered resume (and its rejection on the wrong side), learning to completion, a direct review with a wrong move returning the expected move, closing it as Again, a clean fast review graded Easy, the repertoire's recall and history, and refusing to review an unlearned line; the terminal demo completed for all three sides; `npm test` passed 12 tests (4 new for memory labels, the timeline and family grouping) and `npm run build` passed. In the browser against the local backend at 1440 by 900 and 375 by 812: learned an Alekhine line as Black, reviewed it with two mistakes then continued (graded Again), chose re-learning on a second review (Again recorded, lesson opened), left an Italian Game lesson at 4 of 18 half-moves and resumed it from the dashboard, dragged d2-d4, switched to the Walnut theme with Merida pieces, and saw no console errors or horizontal overflow. The commit hash is assigned by this entry's landing commit.

## Implement the opening catalog structure

On 2026-11-13, implemented the [opening catalog structure](topics/opening-catalog/opening-catalog.md) in the backend and the frontend Learning list. `opening_families.family_side` is now required and only `white` or `black`; Accepted and Declined families are folded into their gambit (Queen's Gambit, King's Gambit and Danish Gambit created); Four Knights Game is White; `opening_lines.side_in_games` is dropped; `opening_lines.parent_line_id` links each line to the longest shorter line of its family; only lines that no other line extends can be learned or join a repertoire, while existing repertoire lines stay reviewable. `Store.add_line` upserts on `moves_uci`. `Store` upgrades older databases at start-up, keeping line and family IDs and practice data; this replaces the family-split migration from `0d2dc08`. The committed demo database was upgraded this way: 82 families (43 white, 39 black), 2,719 lines, 1,889 learnable. The frontend Learning list shows learnable lines only and labels same-name lines with the moves where they differ. Two choices were settled with the user: parent links stay inside a family, and older databases are upgraded at start-up. The ML opening scripts and their CSV files are unchanged; the retraining plan's catalog query no longer selects `side_in_games`. Reason: apply the decisions of the catalog design review.

Checks with Python 3.13.5 and fsrs from `backend/requirements.txt`, on database copies: the start-up upgrade of the layouts at `0d2dc08`, `5cbe0a6` and `4ef8d43` kept every line's moves and all practice rows, with a clean foreign-key check and idempotent restart; heading line 1591 is refused in Learning over the HTTP API and the controller, leaf 1598 is learned, and repertoire heading 982 is still reviewed; `add_line` upsert, parent recomputation and side rules behave as recorded; the terminal demo completes for White, Black and Both. Frontend with Node.js 26.13.1: `npm test` passed 4 tests, including a new `distinguishingMoves` test; `npm run build` passed; the live Learning page listed 1,889 lines with distinct labels on same-name lines and no console errors. The committed demo database is the start-up upgrade of the previous seed (sha256 `5eb848f1…`); practice data from a local session after the upgrade was left out. Documentation build and freshness check pass; lint reports no new findings beyond the 30 existing errors in `OPEN.md`. The commit hash is assigned by this entry's landing commit.

## Record the accepted opening catalog structure

On 2026-11-13, recorded the decisions of a catalog design review in a new topic, [opening catalog structure](topics/opening-catalog/opening-catalog.md). The decisions: family side is only White or Black; `side_in_games` is removed; Accepted/Declined families merge into their gambit; progress stays per line; same-name lines are told apart by their moves in the frontend; `moves_uci` is a line's permanent identity; lines gain `parent_line_id`; and only subvariations can be learned. Reason: keep the agreed design in a record before implementation, and route its team confirmation through open work. No code, schema or data changed. Catalog counts come from read-only queries on `backend/tempo_demo.sqlite` at `0d2dc08`. The database schema and opening library records link the new topic, and `OPEN.md` routes to it. Brought the hand-written `docs/topics/database-schema/database-schema.html` in step with its record: it described the earlier three-table schema and now shows `opening_families`, the six-field `opening_lines`, the start-up migration note and the link to the new topic. Checks with Python 3.13 and `PYTHONUTF8=1`: the documentation build and freshness check pass. Lint reports no new findings; it still fails on 30 existing "bullet without an owning-doc link" errors in the product to-dos section of `OPEN.md`, the same count as before this change. The commit hash is assigned by this entry's landing commit.

## Plan the retraining on the cleaned opening catalog

Added the [retraining plan](topics/fsrs-training/retraining-plan.md) after the opening catalog lost its short lines in `5cbe0a6`. Both variants (`ml/ml_1000bots/`, `ml/ml_300bots/`) are to be retrained on the binary target, gain one true-recall arm each (MSE against the hidden true recall, diagnostic only), report the error in days, and stop holding datasets. Found that the `ml_300bots` generator cannot run: its catalog file `ml/ml_300bots/openings/opening_lines.csv` is not in the repository. Routed from `docs/index.md` and `docs/open/OPEN.md`; probe scripts kept in `docs/topics/fsrs-training/evidence/2026-11-13-probe/`. Nothing was retrained or deleted. Documentation lint reports no new errors; the build check needs Mistune, which is not installed here. The commit hash is assigned by this entry's landing commit.

probed scheduling error in days on `tempo_v1` val agents → first-run global fit schedules a median 0.27 days early (median absolute error 1.30 days, −10.5 days median on lines with a true interval of 30 days or more), default weights +0.04 days; true intervals up to 1,867 days dominate the mean, about 5 minutes.

## Learning mode: opening variations panel and drag-and-drop moves

On 2026-11-13, on the shared frontend branch `feature/frontend-learning`, the guided Learning session gained a Variations panel beside the board. It lists the lines of the same opening family from the catalog: first the lines that continue the current line, with the moves each one adds, then the other variations in opening-tree order. Learned lines are marked, the shortest unlearned continuation is marked as the suggested next line, and choosing any line starts a Learning session for it with the same side; the completion card offers the suggestion as "Learn next". Pieces can now also be dragged with a mouse or finger and dropped on the destination square; clicking a piece and then a square still works, and only the side to move can be picked up. The grouping logic lives in `frontend/src/lib/variations.ts`. Checks: `npm test` passed 7 tests (4 new for the variation grouping and move numbering), `npm run build` passed, and a browser check at 1440 by 900 against the local backend dragged e2-e4 in Alekhine Defense, clicked e4-e5, switched to the Four Pawns Attack from the panel, and saw a dragged wrong move answered with "Try again". The commit hash is assigned by this entry's landing commit.

## Integrate the browser frontend and fitted FSRS runtime

Combined Zeel's `frontend/` and `backend/` layout with the simulator, opening library, and first training run already on main. Moved the existing SQLite seed byte for byte and used the training run's fitted CSV at `backend/fitted_global.csv`. Excluded installed dependencies and build output. Main advanced to `ce8c46f` during integration. Its database added 78 practice events and six progress rows without changing the catalog or schema. Kept the original tracked seed from `4ef8d43` to exclude those added demo records. Moved the product to-do details into their own record to satisfy strict documentation lint.

Checks passed on Python 3.12 and Node 24: the Black-side terminal retry, an HTTP Learning-to-Review session on a copied seed, the scheduler's 21 fitted parameters, three frontend tests, the production build, 21 ML tests, and the documentation build, freshness check and strict lint. The HTTP session rejected an off-line move, selected the learned line for Review, and saved an Again grade and future due date. Chromium could not start in this environment. The landing commit supplies the source identity.

## FSRS training on synthetic clients

Added `ml/`, a synthetic-client simulator that follows the synthetic clients and review dataset records (three archetypes, practice speed-up, Again on any blunder, 500/1800 ms grading, the seven-column schema), and trained FSRS-6 weights on it. Proposed departures, not accepted by the team: recall decided once per line instead of per move, and extra columns `line_id`, `day`, `timestamp`, `baseline_ms`. Reason: with per-move recall, 93.0% of sessions were Again (22.2% with per-line recall) and the hidden true weights could no longer check a fit. Dataset tempo_v1: 1,000 clients, 97,605 reviews, seed 7; committed in `ml/data/tempo_v1/` (38 MB) with a sha256 manifest and regenerated byte-identical on 2026-11-12. Results on 200 unseen val clients, log-loss of pass prediction: default FSRS-6 0.3930, global fit 0.3910, true weights 0.3849; about 100 clients reach the plateau; per-client fits did not help (py-fsrs returns defaults below 512 reviews). Synthetic data only; the true memory model is FSRS-6, so results are optimistic. Checks: 21 FSRS-6 tests pass against py-fsrs 6.3.2. Record: [FSRS training](topics/fsrs-training/fsrs-training.md); experiment: `ml/runs/2026-11-11-first-training/SUMMARY.md`. The commit hash is assigned by this entry's landing commit.

## Opening library with White/Black side

Added `ml/openings/`: the Lichess chess-openings list (3,865 lines, CC0) and `classify.py`, which adds ECO group, family, variation, line length and a hand-set side for every base opening (69 white, 70 black, 1 both); Accepted/Declined families follow their base gambit. `side_evidence.py` checked the sides on 2,806,195 real Lichess games from two days: 92 of 93 families with a clear verdict agree; the exception is Benko Gambit Declined. All lines replay legally with python-chess and the name split rebuilds every original name. Side labels await team confirmation. Record: [opening library](topics/opening-library/opening-library.md). The commit hash is assigned by this entry's landing commit.

## Bring the latest demo data into the frontend branch

On 2026-11-12, merged main at `dc4678d` into `feature/frontend`. The incoming tree changes add `demo/fitted_global.csv`, `demo/synthetic_reviews.csv` and `demo/tempo_demo.sqlite` without conflicts. Verified the staged demo files match main and that the merge changes no frontend files. Builds and backend runtime tests were not rerun because no source or dependency inputs changed; the demo data was imported unchanged. The merge commit supplies the source identity.

## Merge main into the frontend branch

On 2026-11-12, merged main at `4b2824d` into `feature/frontend` to bring the team's current backend, architecture documentation and GitHub Pages configuration into the frontend branch. Resolved the single conflict in `docs/index.md` by retaining the frontend route and all routes from main. The frontend TypeScript check and production build passed through `npm run build`. Backend runtime tests and documentation rendering were not rerun: their source was imported unchanged from main, and the manual resolution only combines documentation links. The merge commit supplies the source identity.

## TEMPO practice backend and presentation walkthrough

Added the practice controller, ML controller, FSRS runtime, and SQLite schema for Learning and Repeating. Added the offline synthetic review generator and a Windows launcher for the local demo. The documentation site now links the System Architecture and End-to-End Flow pages from the sidebar. Verified all four review grades using the supplied weights, persisted stability and due dates, and reproduced the 50,400-session synthetic CSV. The documentation build, freshness check, and lint passed. Generated site files and local demo data are Git-ignored. The landing commit supplies the source identity.

## Review dataset schema and human calibration topic record

Created the canonical topic record (`docs/topics/review-dataset/record.md`) and page source (`docs/topics/review-dataset/index.md`) defining the CSV review session schema (`agent_name, opening_name, review_status, t_days, grade, total_time_ms, accuracy`), the normalized 4-point FSRS grading function based on blunder status and cognitive delay ($\bar{\Delta}$), and the Stage 2 human telemetry calibration pipeline. Registered the topic in `docs/site/site.toml` and `docs/index.md`. No application code was implemented.

## Synthetic client cognitive and behavioral model topic record

Created the canonical topic record (`docs/topics/synthetic-clients/record.md`) and page source (`docs/topics/synthetic-clients/index.md`) defining the cognitive traits, log-normal hesitation sampling, practice-based automaticity decay, FSRS retrievability, and soft blunder penalties for simulated players. Registered the topic in `docs/site/site.toml` and `docs/index.md`. No application code was implemented.

## Shared TEMPO context in the project context

Merged the team's shared TEMPO background (product purpose, vocabulary, the two modes, review planner, FSRS, synthetic clients, the four parts in scope, the earlier prototype and agent guidelines) into `docs/PROJECT_CONTEXT.md`, replacing the starter's placeholder purpose line. Reason: `AGENTS.md` makes that file the one orientation every agent reads first, and the kit names it the canonical home for project purpose, so a separate context file would go unread or duplicate it. The starter's repository map, build and review sections are kept unchanged. Only the Repeating Mode behaviour and synthetic training data are recorded as decided; everything under "What we are building now" stays open for team discussion. No build or application behaviour was measured. The commit hash is assigned by this entry's landing commit.

## Starter origin

Created a neutral documentation example with a project-owned page registry, a shared build-sheet theme and a visual guide. No application behavior or benchmark was measured. No consumer build or browser result is claimed by this template. The repository commit containing this file supplies its initial source identity.
