# FSRS training on synthetic clients

## Scope

This record owns fitting FSRS-6 parameters, evaluation, artifacts and dated
synthetic experiments. [Synthetic Players](../synthetic-clients/record.md)
owns producers, hidden memory and collection policy; [Review Dataset](../review-dataset/record.md)
owns observable schema, grading and future human calibration. Setup belongs
to [ML development](../../development/ml.md), catalog inputs to [Catalog & data](../catalog-data/catalog-data.md),
and runtime scheduling to [App & practice](../app-practice/app-practice.md).

Status: implemented and historically measured on synthetic data only.
The earlier 1,000-client simulator was removed on 2026-11-14; results remain
below. This 2026-11-15 consolidation executed no new numerical experiments.

## Fitting and state replay

`fsrs/model.py` implements vectorised long-term FSRS-6 with 21 weights,
defaults and bounds matching py-fsrs 6.3.2. It does not replay the runtime
scheduler's learning-step states. `load_cards` keys a card by
`(agent_name, opening_name)` and pads its rows into arrays. Rows must already
be chronological within each card; the loader preserves CSV order without
sorting or validating chronology. Package repertoire sampling guarantees
unique names per client; arbitrary human exports do not inherit that rule.

The first row initializes stability/difficulty from the grade; its
pre-review prediction is NaN. Later rows predict recall before applying
the grade. Elapsed time below one day uses short-term stability; later
sessions use recall/forget updates. `predict_states` also returns stability
after every valid row, including initialization; padding stays NaN.

The loss mask contains only `review`/`relearning` rows at least one elapsed
day after the previous session, never a card's first row. Guided rows and
short-delay reviews still update state; they are neither negative examples
nor discarded from replay. Binary success is `grade > 1`, which under the
[session grading rule](../session-grading/session-grading.md) means at most
L(M) mistakes. Since 2026-11-16 `load_cards` uses the app clock by default:
whole elapsed days, the floor of the exported `t_days` (`clock="app"`), as
the app's py-fsrs scheduler counts them; `clock="exact"` keeps the
floating-point `t_days` (rounded to four decimals by the package), the
clock of the 2026-11-13 and 2026-11-14 studies. `load_cards` also reads
each card's player move count M from `repertoires.csv` (`line_lengths`) and
each review's `accuracy`.

`split_clients` shuffles within each archetype using the seed (default 7),
allocates rounded 20% test and 10% validation, and fits on the remainder.
Test clients do not fit general weights; validation selects personalization
settings when enabled. The dated studies also use separately generated
hold-out clients.

Since 2026-11-16 the CLI selects an **arm** (`--arm`); the meaning of R and
the two per-move targets are decided in the
[move recall record](../move-recall/move-recall.md#34-training-arms) and
described in [training approaches](../move-recall/approaches.md):

| CLI arm | R means | Fit target and objective | Boundary |
|---|---|---|---|
| `line` (default) | the line | Mean binary cross-entropy of R against `grade > 1` | The earlier `--target pass`; predictions use session fields |
| `pass` | one move | Mean binary cross-entropy of `p_pass(R, M)` against `grade > 1` | Needs M per card |
| `accuracy` | one move | Binary cross-entropy of R against the review's accuracy, weighted by M (the binomial likelihood of the mistakes) | Needs M per card |
| `true-recall` | one move | As `accuracy`, against the hidden per-move recall on fit clients | Diagnostic only; unavailable for real players. Replaces the earlier `--target true` (MSE against hidden `p_clean`) |

`Objective` computes the arm's loss and its exact gradient with the torch
replay in `fsrs/torch_model.py`, on a CUDA GPU when available (`--device`);
`fsrs/model.py` stays the numpy reference, and tests check that both give
the same loss and that the gradient matches finite differences. The loss
optionally adds an L2 pull toward a prior, normalized by each parameter's
allowed range. `fit` clips starting weights and uses SciPy L-BFGS-B with
FSRS bounds, `maxiter=2000`, `ftol=1e-12` and `gtol=1e-7`. It records loss,
iterations, evaluations, convergence, termination message, the largest
projected gradient and the device. Saving weights proves neither
convergence nor a global optimum. Until 2026-11-16 `fit` used
finite-difference gradients (step 1e-6), `maxiter=300` and SciPy's default
tolerances; the dated studies below used that version.

Personalization is implemented and optional, not an accepted rollout policy.
Without `--no-personalise`, the first 60% of each client's tested rows fit
local weights and the remaining 40% score them; CSV order supplies time
order. Fewer than ten tested rows gives no time split; fitting additionally
requires ten early and five late rows. Local fits start from general weights
with at most 100 iterations. Validation selects the L2 strength from
0.01/0.1/1/10; late test results compare defaults, general and personalized
predictions. Local fitting uses the general arm's loss. The dated arms skip
personalization.

## Evaluation metrics

`evaluate.metrics.score` computes probability metrics on the loss mask,
then days metrics on **every valid session**, guided rows included. Its
`link` says how the fitted R becomes a pass prediction: `line` uses R,
`move` uses `p_pass(R, M)`. The
constant baseline is the fit clients' binary success rate; it has no
state-based days prediction.

| Output | Definition / unit |
|---|---|
| `log_loss` | Mean binary cross-entropy, natural logs, nats/review; probabilities clipped to 1e-6 through 1 minus 1e-6 |
| `brier` | Mean `(prediction - outcome)^2`, probability squared |
| `rmse_bins` | Weighted RMSE of mean prediction versus observed success in 20 equal-width probability bins; probability |
| `auc` | Rank AUC with averaged tied ranks; assumes both classes occur |
| `rmse_vs_truth`, `mae_vs_truth` | Error against the hidden pass chance `p_pass` (before 2026-11-16 `p_clean = R^M`); probability, ×100 for percentage points |
| `move_recall` | Per-move arms only: RMSE and MAE of R against the hidden per-move recall |
| `mean_predicted`, `observed_success`, `reviews` | Mean prediction, success rate and masked count |

`Truth` reads `ground_truth.csv` and C from `clients.csv`, aligning through
`Cards.row` by CSV position. It does not join or validate identity/hashes.
Preserve row alignment and verify the generator manifest before relying on
independently supplied sidecars. Hidden truth is evaluation data and, for
B-arm diagnostics, a target for **fit clients only**, never a planner input.

### Days metric

Since 2026-11-16 ([move recall record, section 3.5](../move-recall/move-recall.md#35-evaluation-follows-the-pass-meaning)):
error is predicted minus true days until the chance of **passing** the line
(at most L(M) mistakes) falls to 90%; negative means an early review.
`evaluate.days.true_days` uses hidden stability after the session S, move
count M, client C and the per-move target `R*(M)` at which
`p_pass(R*, M) = 0.9`:

`F = 0.9**(-1/C) - 1`

`d_true = S / F * (R*(M)**(-1/C) - 1)`

A line-link arm predicts its fitted stability; a move-link arm predicts the
same expression with its fitted stability and decay w20. For one move this
equals S.

Accepted on 2026-11-13 and used by the dated studies below: the chance of a
**clean** session, `d_true = S / F * ((0.9**(1/M))**(-1/C) - 1)`. Days results
under the two definitions are not comparable. The removed simulator sampled once per line,
so its true days simply equaled hidden stability; do not interchange these
definitions. The 90% threshold expresses the team's requested stability
difference and matches the app's default desired retention. Medians were
chosen because the motivation probe contained intervals up to 1,867 days
that dominated means.

Report median error, median absolute error, median relative error
(`error / d_true`, stored as fraction), mean error, share too early,
median true/predicted days and count beyond the horizon. The three medians
are also split by true interval below 7, 7 to below 30, and at least 30 days,
and by after-learning versus after-review. Means are sensitive to long
intervals; values beyond the horizon are extrapolations the simulated
history cannot verify. The accepted protocol called for dropping missing
true days; current code expects complete aligned truth and does not
explicitly filter missing/non-finite values. This is a precondition, not
robust arbitrary human-data ingestion.

## Artifacts and reproduction

The trainer writes `fsrs6_general_parameters.json` (model/target/loss,
rounded fitted/default weights and fit-data counts), `metrics.json`
(test, per-archetype, fit, optimizer, baseline, client split, environment and
seconds), and optionally `personalisation_test_clients.csv`. Metrics record
Python/NumPy/pandas/platform; the experiment record must retain SciPy and
complete producing-source identity.

Generated data stays ignored; each experiment's `dataset_MANIFEST.txt`
retains identities and rebuild instructions. [ML development](../../development/ml.md)
commands exercise the current package. Exact historical reproduction also
needs the dated source pin/diff, catalog content hash, config, environment
and local scoring scripts. Today's catalog does not reproduce the earlier
91-family input. This documentation work regenerated no data or results.

## Multiplicative memory: arms A2 and B2

Recorded run: [FSRS-6 on the cleaned catalog, pass/fail vs true recall
(2026-11-13)](../../../ml/experiments/2026-11-13-fsrs-synthetic-v2/SUMMARY.md),
arms A2 and B2 of the [accepted comparison](#accepted-comparison-and-retired-protocol). It holds two
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
arms A1, A1c and B1 of the [accepted comparison](#accepted-comparison-and-retired-protocol), with the
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

## Per-move recall under the decided grading rule (2026-11-16)

Run: [line-level versus per-move FSRS](../../../ml/experiments/2026-11-16-move-recall/SUMMARY.md),
protocol fixed in its [PLAN.md](../../../ml/experiments/2026-11-16-move-recall/PLAN.md).
FSRS hidden memory, the decided [grading rule](../session-grading/session-grading.md),
app clock, three populations of 300 clients (seeds 20261111, 20261121,
20261131) and 60 hold-out clients each. Arms as decided in the
[move recall record](../move-recall/move-recall.md#34-training-arms):

| Arm | Trainer | R means | Target | File per seed |
|---|---|---|---|---|
| A1 | py-fsrs 6.3.2 `Optimizer` | the line | pass/fail | `results/seed-<s>/A1/fsrs6_general_parameters.json` |
| A1c | `tempo_ml.fsrs.train --arm line` | the line | pass/fail | `results/seed-<s>/A1c/…` |
| A1c-pass | `--arm pass` | one move | pass/fail through `p_pass(R, M)` | `results/seed-<s>/A1c-pass/…` |
| A1c-acc | `--arm accuracy` | one move | accuracy, weighted by M | `results/seed-<s>/A1c-acc/…` |
| A1c-R | `--arm true-recall` | one move | hidden per-move recall (diagnostic) | `results/seed-<s>/A1c-R/…` |

Test log-loss, mean of the seeds (22,851 reviews, 92.7% passed):
defaults 0.2123, A1 0.2033, A1c 0.2029, A1c-pass 0.1902, A1c-acc 0.1900,
A1c-R 0.1898, perfect predictor 0.1848. Against the perfect predictor the
line-level arms close 33–34% of the gap and the per-move arms 80–81%
(hold-out 30–31% and 75–76%). By the plan's bar, per-move recall beats
line-level recall (A1c → A1c-pass −0.0121, 95% [−0.0143, −0.0099], all
seeds); the two per-move targets show no difference, also on the first 60
days only; A1 against A1c is inconclusive (−0.0003, seeds disagree). Median
absolute days error: per-move arms 5.5–5.8 days, A1 8.5, A1c 11.5, defaults
6.4. All 21 shared-trainer fits converged. Days results use the 0.9
pass-chance definition and are not comparable with the two studies above.
Simulated clients only; limits and attempts are in the run's summary.

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
diagram is source-authored from the Synthetic Players simulator/app comparison;
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
| 90% threshold; error = predicted minus true days; negative means early | Days metric in this record; this record's result/limit sections |
| 91 versus 82 families in the dated runs | Each run's Inputs; Historical evidence gaps above |
| Runtime old first-fit weights from 800 synthetic clients; py-fsrs 6.3.2 | Earlier 1,000-client simulator section above |
| B2 and A1c reached the 300-iteration limit | Each experiment's optimizer observations; no convergence inferred |

The dated experiment summaries and complete result artifacts are retained
unchanged; the page's selected tables are a new view of those historical
results, not replacement evidence or a rerun. Figure/chapter numbers and
dated run names are presentation identifiers. Setup commands come from
[ML development](../../development/ml.md), rather than retired variant paths.

## Accepted comparison and retired protocol

The completed/superseded `retraining-plan.md` was retired in the authorized
2026-11-15 consolidation. Its full task text, historical layout mapping,
proposed paths and original open questions remain at
[commit 788e06039dd2869b23261dd80ea8fc49367ab33c, docs/topics/fsrs-training/retraining-plan.md](https://github.com/davszi/Tempo/blob/788e06039dd2869b23261dd80ea8fc49367ab33c/docs/topics/fsrs-training/retraining-plan.md).
It is historical protocol, not current execution instructions.

Durable decisions from the 2026-11-13 discussion:

- Keep binary training and compare true-recall MSE diagnostics using the
  same data/split. A2/B2 and A1c/B1 isolate target/loss within each study.
  A1/A1c compare trainers with the same target, with explicit clock treatment.
  Cross-study comparisons have the documented 91/82-family catalog confound.
- Keep A1c as B1's binary control. Each arm returns one global set of 21
  weights; per-player fitting is outside these arms.
- Never copy diagnostic true-recall B-arm weights to
  `backend/fitted_global.csv`. Choosing the demo's binary weights remains
  unresolved. Read catalog inputs read-only; do not commit generated data.
- Keep evaluation clients separate from fitting and setting selection;
  report probability and 90%-days metrics as defined above.
- The original removed-simulator recovery gate required identifiable weights
  (all except w0, w1, w3, w19) within 10% of generating weights and validation
  truth RMSE below 0.005. It also required 100 random-card replays to agree
  between implementations within 1e-9 and zero MSE at generating parameters.
  This historical gate does not establish exact recovery by the current
  per-move, lapse-floor generator. The inspected current unit test instead
  checks loss improvement and a 0.005 loss bound; no recovery run was made
  in this documentation pass.

The original investigation bound was about one hour of laptop CPU, stopping
after five arms. Changed settings after evaluation required a new recorded
attempt. A1/A1c/B1 ultimately used package FSRS memory instead of the removed
simulator. Each dated experiment keeps its actual scope, settings, attempts
and original environment. The removed `fsrs-synthetic-v1` run and HTML page
remain retrievable at `09f8a22`; the removed 1,000-client variant at `825e9d8`.

## Motivation probe (2026-11-13)

A probe on the old `tempo_v1` val agents (200 agents, 18,631 reviews) scored
the first run's global fit against the hidden truth.

| | default FSRS-6 | global fit, first run |
|---|---|---|
| RMSE against true recall | 4.8 pp | 3.5 pp |
| MAE against true recall | 3.0 pp | 2.5 pp |
| days: median error | +0.04 | −0.27 |
| days: median absolute error | 1.48 | 1.30 |
| days: median error, true interval 30 days or more | −5.8 | −10.5 |

- The log-loss, RMSE(bins) and AUC from the same run reproduced the published
  values in [FSRS training](fsrs-training.md#earlier-1000-client-simulator-removed) exactly.
- This probe measured days to each player's own target retention (80–95%),
  not the 90% proposed above, so its days numbers are motivation, not
  baselines for this plan.
- Source: commit `e130687`. The inputs are unchanged in `5cbe0a6`.
- Environment: Python 3.12.12, numpy 2.3.5, Windows 11.
- Scripts: [`evidence/2026-11-13-probe/`](evidence/2026-11-13-probe/). Run
  them from the repository root:
  - `python -I docs/topics/fsrs-training/evidence/2026-11-13-probe/accuracy_check.py ml/ml_1000bots`
  - `python -I docs/topics/fsrs-training/evidence/2026-11-13-probe/days_error.py ml/ml_1000bots`

## Open research and implementation choices

- Which binary arm's weights should the demo load? Runtime still uses the
  removed simulator's first global fit. Replacing it needs a separate
  decision; B-arm diagnostic weights remain excluded.
- Whether to rerun historical `agent_curve.py` and per-player experiments
  on the cleaned catalog remains undecided; neither A/B study required it.
  Source support for personalization is not a real-player rollout decision.
- The retired plan asked whether collection should use family popularity
  and where the catalog build should live. Current collection is uniform
  because SQLite has no popularity field. [Catalog & data](../catalog-data/catalog-data.md)
  owns build/provenance; changing collection weighting needs an agreed
  experiment scope. Migration did not silently accept the old proposal.

## Retained study drivers

The six Python files directly under the two retained `ml/experiments/`
directories are study-owned drivers, not additional package entrypoints or
app runtime code. A bounded 2026-11-15 extension read all six against their
`SUMMARY.md` protocols; none was executed. The summaries retain run settings,
environments, historical checks and results. This table fills the source
ownership and reproduction boundary without qualifying those runs again.

| Study / driver | Inputs and operation | Outputs / boundary |
|---|---|---|
| `2026-11-13-fsrs-synthetic-v2/holdout_benchmark.py` | `--data`, named parameter JSON files and explicit fit-client `--base-rate`; scores defaults and supplied weights on every client, overall and by archetype | `--out` JSON; no fitting or new client split; exact exported elapsed-time replay |
| `2026-11-13-fsrs-synthetic-v2/compare_v1.py` | Fixed package data paths, A2/B2 files and v1 parameters retrieved through `git show 09f8a22:ml/ml_300bots/ml_engine/experiments/fsrs-synthetic-v1/results/fsrs6_general_parameters.json`; recreates seed-7 test membership, scores test and all hold-out clients | `results/v1_comparison.json`, including all weight sets; no fitting; needs reachable Git history and matching datasets |
| `2026-11-13-fsrs-synthetic-v2/benchmark_data.py` | Reads binary/true-recall metrics, hold-out and v1 comparison JSON; formats probability, days, archetype, optimizer and weight tables | `results/benchmark-data.md`; reporting only, with some hardcoded historical text/numbers described below |
| `2026-11-14-fsrs-memory/train_pyfsrs.py` | Sessions, client split and row-aligned simulation day; sends **fit clients only** to py-fsrs `Optimizer`; then scores default/fitted weights on test clients with exact and calendar replay | A1 parameter JSON and metrics JSON; actual fitting; calendar timestamps derive from floored simulation days, not hidden recall probabilities |
| `2026-11-14-fsrs-memory/score_all.py` | Saved A1/A1c/B1 weights, train and hold-out datasets; recreates split, derives the constant from fit clients and scores test/all hold-out clients under both clocks | `results/scores.json`; no fitting; paired review-weighted log-loss gains from 1,000 whole-client bootstrap resamples (bootstrap seed 0) |
| `2026-11-14-fsrs-memory/tables.py` | Results directory's `scores.json`; rounds/formats both sets/clocks, paired intervals and days bands | `results/tables.md`; reporting only, with the sign-legend discrepancy below |

Paths in the first column are relative to `ml/experiments/`. These commands
write or replace their named artifacts; reading their source is distinct
from invoking them. Exact reproduction still needs each summary's producing
source, input identities and environment. Drivers reuse the package's
row-aligned truth loaders and do not independently verify dataset hashes,
sidecar alignment or evaluation membership against saved training metadata.
Changing a split seed during scoring can therefore change the claimed test
cohort; it must match the fitted run. A1's `--seed` controls client splitting,
not an explicit optimizer/Torch random seed in this script. Its optimizer
settings are dependency defaults, whose historical versions belong to the
run record.

### Clock, presentation and uncertainty limits

`train_pyfsrs.review_logs` stamps every fit session at UTC midnight on
`2026-01-05 + floor(simulation day)`, carrying grade and duration. It does
not use hidden recall probabilities as A1 fit targets. `calendar_cards`
replaces elapsed values with differences between floored simulation days
but preserves the **original exact-clock loss mask**. Thus exact/calendar
probability comparisons retain the same review cohort; they do not each
reselect rows using their own one-day threshold. Both clocks update state
through the full session history. Days errors retain the same hidden true
intervals while their predicted states follow the selected replay clock.
Calendar-day scoring does not establish that the live app uses that same
clock convention for every scheduler operation.

`score_all.paired(wa, wb)` computes loss(wa) minus loss(wb). Its comparison
keys are `wb vs wa`, so a **positive gain favors the first-named weights**.
The retained `tables.py` emits a legend saying positive favors the
second-named weights; that legend is reversed relative to the computation.
Use the source-defined sign and raw JSON when interpreting those historical
comparison rows. This documentation pass changes neither the driver nor
the retained table.

`benchmark_data.py` predominantly formats retained JSON, but also embeds
historical fit-objective values 0.560232 and 0.553194 and cohort/split text
as literals. Its generated claim that every number is unrounded and none
was typed by hand is broader than its implementation: tables explicitly
round values and those fit objectives are not recomputed there. Those
figures remain historical observations attributed to the dated study,
not newly verified calculations or wholly JSON-derived output. No driver
was run to reproduce weights, scores, intervals, tables or data in this pass.

## Source coverage and verification limits

The bounded 2026-11-15 source pass at
`788e06039dd2869b23261dd80ea8fc49367ab33c` read every package file, four
configs, package metadata, four ML test files, the backend demo producer
and both dated experiment summaries. It filled replay/mask, optimizer,
personalization, metric, truth-alignment, artifact and reproduction gaps.
Source facts and historical measurements remain distinct.

| Source / symbols | Canonical section |
|---|---|
| `ml/tempo_ml/fsrs/model.py`: parameters/bounds, step functions, `predict`, `predict_states`, `Cards`, `load_cards` | Fitting and state replay; Days metric |
| `ml/tempo_ml/fsrs/train.py`: `objective`, `fit`, `split_clients`, `time_split`, `personalise`, `main` | Fitting and state replay; Artifacts and reproduction |
| `ml/tempo_ml/evaluate/metrics.py`: `bce`, `auc`, `rmse_bins`, `metrics`, `Truth`, `score` | Evaluation metrics |
| `ml/tempo_ml/evaluate/days.py`: `TARGET_RETENTION`, `true_days`, `days_metrics` | Days metric |
| Package, `fsrs/`, `evaluate/` `__init__.py` files | Package scope; app runtime planner is separate |
| `ml/pyproject.toml`; CLI arguments | ML development guide |
| `ml/tests/test_trainers.py`, `test_metrics.py` | Inspected reference-formula/bounds, masks, replay/padding, client split, loss improvement, AUC, truth/day and zero-MSE assertions |
| Six retained `ml/experiments/*/*.py` drivers | Retained study drivers: inputs, outputs, fit/score/report boundary, clock cohort and historical presentation limitations; inspected without execution |

Tests were inspected, not executed. No training, benchmark, generation,
app run or human calibration occurred. No new numerical equivalence,
convergence or performance claim follows. Every current `--arm` still
requires synthetic truth sidecars; production human export/fitting remains
future work in [Review Dataset](../review-dataset/record.md). Missing-data
robustness, single-class AUC, arbitrary human chronology and calibration
qualification remain outside demonstrated package coverage.


## Retained retraining plan and ML setup guide

The two earlier cleanup decisions are resolved by this consolidation. The
completed plan is retired after its accepted criteria and unique motivation
probe were absorbed above; [Accepted comparison and retired protocol](#accepted-comparison-and-retired-protocol)
retains its exact historical Git identity. Package setup now lives in
[ML development](../../development/ml.md), leaving only the repository-root
README. This section records that closure for historical links; it is not a
second requirements owner or an active cleanup request.
