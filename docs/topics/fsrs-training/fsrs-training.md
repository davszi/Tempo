# FSRS training on synthetic clients

## Scope

This record owns the synthetic-client simulator in the package `ml/tempo_ml/`,
its two hidden memory models, how FSRS-6 weights are trained and evaluated on
them, and the results. The client model and the dataset schema are specified
by the team in the [synthetic clients record](../synthetic-clients/record.md)
and the [review dataset record](../review-dataset/record.md); this record
only states how the code follows them and where it adds to them. The opening
lines come from the team's catalog in `backend/tempo_demo.sqlite`
([opening catalog structure](../opening-catalog/opening-catalog.md)).

Status: implemented and measured on synthetic data only. The earlier
1,000-client simulator `ml/ml_1000bots/` was removed on 2026-11-14; its
results are kept under [earlier 1,000-client simulator](#earlier-1000-client-simulator-removed).

## Simulator and package

Code: `ml/tempo_ml/` (install and run: `ml/README.md`). Each move is recalled
on its own and a session passes only when every move is right; a wrong move
is retried. Clients learn 1–3 new lines a day and are tested 3 minutes later;
reviews follow a grade-based interval policy. The generator reads the catalog
from `backend/tempo_demo.sqlite`; a line is offered to the side of its family.

The hidden memory model is chosen in the generation config:

| `memory` | Model | Per client | After a clean session | After a lapse |
|---|---|---|---|---|
| `multiplicative` (default) | `simulator/memory/multiplicative.py` | decay C | stability × (1 + 1.5·e^(2(1−R))) | min(previous stability, max(1 day, stability × 0.3)) |
| `fsrs` | `simulator/memory/fsrs.py` | 21 FSRS-6 weights, w20 = C | short-term update when elapsed time < 1 day; otherwise recall update with the line's difficulty | short-term or forget update, clamped to min(previous stability, max(1 day, updated stability)) |

Both use the forgetting curve of the synthetic clients record, section 3.2.
The FSRS-6 weights are the defaults with log-normal noise (sd 0.15) on w0–w16,
w17–w19 at the defaults, drawn from their own random stream; with the same
config apart from `memory`, both models give the same clients, sides and
repertoires. Selecting `fsrs` leaves the multiplicative model unchanged: its
generator output is byte-identical before and after `fsrs` was added.

The byte-identity claim is the check recorded in the 2026-11-14 experiment,
using the same catalog for both configurations; it is not a fresh run on
the current working tree. The published A2/B2 and A1/A1c/B1 runs used
different catalog groupings (91 and 82 families respectively), so their
results do not isolate the memory-model change alone.

## Simulator, app and accepted specification

The package is an offline data generator and trainer, not the app's runtime
planner. `backend/ml_engine.py` uses py-fsrs `Scheduler`; it selects the
oldest due line and uses a grading baseline of 0 ms unless configured.
`tempo_ml.simulator.practice` instead uses grade-based noisy intervals and
each synthetic client's known physical baseline. The app stores move events
in SQLite, while the package writes the review-session CSV schema.

Learning also differs: the package records and grades each guided session,
updates hidden memory, then tests the line after the session duration plus
three minutes. In the app, finishing Learning initializes a due card but
does not grade it or initialize its stability; the first Repeating session
does that (`backend/ml_controller.py`, `initialize_progress` and
`complete_review`). The package samples any eligible catalog line, with
unique names within a client's repertoire; the app admits only lines that
no other catalog line extends. The package permits at most five attempts
per move, whereas the app supports retries and explicitly stopped reviews.
These are implemented differences, not accepted changes to the product
requirements. Their effect on transfer from synthetic training to the app
has not been measured.

The accepted cognitive and dataset specifications remain in their owning
records. Package-specific additions and unresolved retry semantics are
identified in the [synthetic clients record](../synthetic-clients/record.md#6-implementation-and-open-choices).
Human calibration is specified for a later stage; no implemented calibration
pipeline or human validation is established by these synthetic experiments.

## Multiplicative memory: arms A2 and B2

Recorded run: [FSRS-6 on the cleaned catalog, pass/fail vs true recall
(2026-11-13)](../../../ml/experiments/2026-11-13-fsrs-synthetic-v2/SUMMARY.md),
arms A2 and B2 of the [retraining plan](retraining-plan.md). It holds two
trained weight sets:

| Weights | Trained on | Loss | File |
|---|---|---|---|
| A2 | pass/fail of each session | log-loss | `results/binary/fsrs6_general_parameters.json` |
| B2 | hidden true chance of a clean session | MSE | `results/true-recall/fsrs6_general_parameters.json` |

Conclusions, scoped to these synthetic clients (60 test clients; 60 hold-out
clients agree):

1. Training halves the error against the true chance: defaults 27.7 pp,
   A2 14.1 pp, B2 13.8 pp. Calibration (RMSE(bins)) goes from 19.2 to 2.6 pp.
2. Training on the true chance adds 0.3 pp over pass/fail, so pass/fail, the
   target available for real players, performed nearly as well in this run.
   This does not establish its sufficiency for real players.
3. In days to a 90% pass chance, A2 and B2 schedule a median 0.14 and
   0.10 days early, and 45–47 days early on lines whose true time is 30 days
   or more.
4. The earlier v1 weights, trained on the old catalog, score 13.1 pp on the
   same clients and a lower training loss than A2 on A2's own fit clients:
   A2's fit, started at the defaults, stopped in a worse local optimum.

## FSRS memory: arms A1, A1c and B1

Run: [FSRS-6 on clients whose hidden memory is FSRS-6
(2026-11-14)](../../../ml/experiments/2026-11-14-fsrs-memory/SUMMARY.md),
arms A1, A1c and B1 of the [retraining plan](retraining-plan.md), with the
configuration, split, trainer settings and metrics of A2 and B2.

| Weights | Trainer | Trained on | Loss | File |
|---|---|---|---|---|
| A1 | py-fsrs 6.3.2 `Optimizer` | pass/fail | log-loss | `results/pyfsrs/fsrs6_general_parameters.json` |
| A1c | `tempo_ml.fsrs.train` | pass/fail | log-loss | `results/binary/fsrs6_general_parameters.json` |
| B1 | `tempo_ml.fsrs.train` | hidden true chance of a clean session | MSE | `results/true-recall/fsrs6_general_parameters.json` |

Conclusions, scoped to these synthetic clients (60 test clients, 38.4% of
reviews pass; 60 hold-out clients agree):

1. The defaults predict 67.7% and score worse than a constant (log-loss
   0.8307 vs 0.6661). A1c and B1 predict within 1 pp of the observed rate,
   reach 0.6084 and 0.6091, and close 86% of the gap to a perfect predictor
   (0.5735). The error against the true chance falls from 32.5 to 12.2 pp.
2. Training on the true chance adds nothing: B1 is 0.0008 log-loss worse than
   A1c (95% interval 0.0004 to 0.0012).
3. A1 scores 0.7135 on exact elapsed time but 0.6127 on calendar days, the
   clock py-fsrs trains on; there A1c scores 0.6117 and the two do not differ
   (interval includes zero). This comparison did not establish a trainer
   advantage on the calendar-day clock; training and scheduling must use
   compatible elapsed-time conventions.
4. Trained weights call about 89% of reviews early; on lines whose true time
   is 30 days or more, the median error is −21 days for A1c and −11 for B1.

## Earlier 1,000-client simulator (removed)

`ml/ml_1000bots/` held a separate simulator with FSRS-6 hidden memory, recall
decided once per line, the app's FSRS-6 scheduler and 1,000 clients. It was
removed on 2026-11-14 in favour of the package above; its last committed
state, including the dataset `tempo_v1`, the opening library build in
`openings/` and the first training run in `runs/2026-11-11-first-training/`,
is at commit `825e9d8`.

`backend/fitted_global.csv`, read by the web and terminal demos, is a
byte-identical copy of that first run's weights (checked 2026-11-12): one
global fit with py-fsrs 6.3.2 on 800 clients, trained on the catalog before
commit `5cbe0a6`.

| tempo_v1 val (200 clients) | log-loss | RMSE(bins) | AUC |
|---|---|---|---|
| default FSRS-6 | 0.3930 | 0.0335 | 0.670 |
| global fit | 0.3910 | 0.0201 | 0.670 |
| true weights (oracle) | 0.3849 | 0.0126 | 0.692 |

Conclusions of that run, scoped to those clients:

1. The global fit closed 25% of the default-to-oracle gap on the val clients
   (95% bootstrap interval 11%–37%) and 48% on 200 new clients; most of the
   gain was calibration. The decay C moved from 0.15 to 0.43 (true median
   0.49).
2. About 100 clients (about 10,000 reviews) reached the plateau of the
   global fit.
3. Per-client fits did not help after 4 months of data.
4. The fit could not recover w0, w1, w3 (every Learning session was logged as
   grade 3) or w19 (no same-day reviews).

Proposals made for that simulator, never accepted by the team: recall per
line instead of per move (synthetic clients record, section 3.3); the extra
dataset columns `line_id`, `day` and `baseline_ms`; and, for the ML engine,
one global fit first, retraining on real data at about 100 players, no
per-player fitting before several hundred reviews, and a quality signal for
Learning sessions so that w0–w3 can be learned.

## Limits

- Synthetic clients only. Under FSRS memory the per-move forgetting curve
  has the FSRS-6 form, but hidden stability also has a lapse floor and is
  updated with the whole session's grade. A line passes with probability
  R^M rather than R. These runs therefore do not demonstrate exact recovery
  of an unmodified FSRS process. Multiplicative memory is not FSRS.
  Which resembles real players is open.
- Trained weights describe synthetic clients. They improve the recorded
  synthetic prediction metrics, not demonstrated human retention. They must
  not ship as real-player weights; retrain on real data. The choice of which
  synthetic weights the demo loads remains a separate open decision below.
- The size of the gain depends on how far the synthetic population sits from
  the defaults.

Not accepted by the team: which weights the app ships; `backend/fitted_global.csv`
still holds the first-run weights of the removed simulator.

## Historical evidence gaps


The FSRS-memory experiment record's exploratory percentages and optimizer
observations at `ml/experiments/2026-11-14-fsrs-memory/SUMMARY.md` describe
uncommitted exploratory code/output that was not retained. Those observations
are not independently reproducible from the retained artifacts. Its opener
also says only hidden memory differed, while its own inputs/caveat show the
catalog regrouped from 91 to 82 families. The current training topic explains
that confound; the historical record is not rewritten by this pass.

Git identifies that experiment's indirect 'landing commit' source as
`ea3d01d7743dac5f513d853e1ef5c0d451e3b105`. A new claim based on the missing
exploratory artifacts needs a retained rerun; this audit does not manufacture
evidence or authorize that experiment. The full current experiment tables
remain distinct from the unretained exploratory observations.

## Page presentation and numeric sources

The authored `index.md` explains the offline/runtime boundary, fitting,
metrics and the two dated synthetic studies separately. Its inline lane
diagram is source-authored from this record's simulator/app comparison;
the fitting flow uses the arm definitions and held-out-client protocols.
No diagram implies that diagnostic weights are deployed.

| Displayed result or configuration | Source and scope |
|---|---|
| FSRS-6; A2/B2 and A1/A1c/B1 arm names | Arm tables in this record and the dated experiment protocols |
| Test groups of 60 clients; additional 60 hold-out clients per study | Dated experiment protocols; synthetic data only |
| A2/B2: defaults/A2/B2 truth RMSE 27.7/14.1/13.8 pp; calibration RMSE 19.2/2.6/2.1 pp; log-loss 0.723/0.562/0.560 | `ml/experiments/2026-11-13-fsrs-synthetic-v2/SUMMARY.md`, Results, test-clients table |
| A2/B2: median days error +0.00/-0.14/-0.10 days; long-interval medians -38.6/-47.0/-45.0 days for true interval at least 30 days | Same run, Results, days metric and interval tables |
| A1 study: exact-clock log-loss defaults/A1/A1c/B1 = 0.8307/0.7135/0.6084/0.6091; truth RMSE 32.5/24.7/12.2/12.3 pp | `ml/experiments/2026-11-14-fsrs-memory/SUMMARY.md`, Results, exact-clock test table |
| Calendar-day log-loss A1/A1c = 0.6127/0.6117 | Same run, Results, clock comparison |
| 90% threshold; error = predicted minus true days; negative means early | Retained retraining plan, Days metric; this record's result/limit sections |
| 91 versus 82 families in the dated runs | Each run's Inputs; Historical evidence gaps above |
| Runtime old first-fit weights from 800 synthetic clients; py-fsrs 6.3.2 | Earlier 1,000-client simulator section above |
| B2 and A1c reached the 300-iteration limit | Each experiment's optimizer observations; no convergence inferred |

The dated experiment summaries and complete result artifacts are retained
unchanged; the page's selected tables are a new view of those historical
results, not replacement evidence or a rerun. Figure/chapter numbers and
dated run names are presentation identifiers. Setup commands come from
`ml/README.md`, not from the retired variant paths in the plan.

## Retained retraining plan and ML setup guide

### Finished retraining plan

`docs/topics/fsrs-training/retraining-plan.md` says its work is completed or
superseded. Kit 4/5 asks to retire finished working documents after lasting
content has a current home and concrete deletion approval. Its accepted
days metric, recovery criteria and diagnostic-weight restriction must be
accounted for first. Recommend that coverage check followed by approved
retirement. The plan is retained pending that decision.

### ML setup guide name

`ml/README.md` is a useful setup guide but kit 5 expects one root README.
Recommend approving a rename to `ml/ML_GUIDE.md`, updating current links and
preserving historical source identities. It remains in place pending approval.
