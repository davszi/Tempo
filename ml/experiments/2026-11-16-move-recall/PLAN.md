# Plan: line-level versus per-move FSRS under the decided grading rule

Written 2026-11-16 before any run. Decisions behind it:
[move recall record](../../../docs/topics/move-recall/move-recall.md) and
[training approaches](../../../docs/topics/move-recall/approaches.md).

## Question and motivation

Under the decided [session grading rule](../../../docs/topics/session-grading/session-grading.md)
a review passes with at most `L(M)` mistakes. Design arithmetic in the move
recall record (section 3.2) shows that one line-level FSRS curve cannot draw
the resulting pass chance across line lengths (worst error 0.136), while FSRS
recall of one move followed by `p_pass(R, M)` can (error 0). This experiment
measures whether that matters on simulated players:

1. **Q1, meaning of R.** Does a per-move model (A1c-pass) predict the pass
   outcome better than the line-level model (A1c), with everything else equal?
2. **Q2, training target.** Between the two per-move approaches, does the
   accuracy target (A1c-acc) predict better than pass/fail through `p_pass`
   (A1c-pass)? Also with less history per player (reduced data)?
3. **Q3, trainer.** Do the official py-fsrs Optimizer (A1) and the shared
   trainer (A1c) differ when both use the app clock?

**Kind.** Investigation. Q1–Q3 are confirmatory: comparisons, metric and bar
are fixed here before any result. Everything else (per-archetype results,
days metric, move-recall error, A1c-R, personalisation) is exploratory.

**Decision informed.** Which weights and which scheduler the team ships
(move recall record, section 7.4), and whether the app needs the per-line
`R*(M)` scheduler.

## Arms

All arms: FSRS-6 hidden memory, the decided grading rule, the current
catalog (`backend/tempo_demo.sqlite`), app clock (whole elapsed days) for
training and scoring, start at the FSRS-6 defaults, split by archetype
(seed 7; fit 70 %, validation 10 %, test 20 %).

| Arm | Command | Trainer | Target | R means |
|---|---|---|---|---|
| A1 | `train_pyfsrs.py` | py-fsrs 6.3.2 Optimizer, defaults, CPU | pass/fail | the line |
| A1c | `tempo_ml.fsrs.train --arm line` | L-BFGS-B, torch gradients, A100 | pass/fail | the line |
| A1c-pass | `--arm pass` | as A1c | pass/fail through `p_pass(R, M)` | one move |
| A1c-acc | `--arm accuracy` | as A1c | accuracy, weighted by M | one move |
| A1c-R | `--arm true-recall` | as A1c | hidden per-move recall, weighted by M (simulator-only reference) | one move |

Shared trainer settings: `maxiter = 2000`, `ftol = 1e-12`, `gtol = 1e-7`.
Personalisation is skipped (`--no-personalise`); it is not part of the questions.

"Trainer" in Q3 is a package of differences, not one setting: optimizer
(Adam, 5 epochs versus L-BFGS-B to convergence), gradients, py-fsrs's own
state replay with learning steps versus `tempo_ml.fsrs.model`, and py-fsrs's
64-review cap per card.

## Data

| Set | Config | Seeds | Clients | Use |
|---|---|---|---|---|
| Train | `configs/fsrs-memory.json` | 20261111, 20261121, 20261131 | 300 (100 per archetype), 180 days | fit / validation / test split |
| Hold-out | `configs/fsrs-memory-holdout.json` | 20261112, 20261122, 20261132 | 60 new clients, 180 days | second evaluation of each seed's weights |
| Reduced | train config, `--horizon-days 60` | the train seeds | the same 300 clients, first 60 days | Q2 with less history |

Reduced-data arms (A1c, A1c-pass, A1c-acc) are fitted on the 60-day data of
the fit clients and scored on the full 180-day test clients of the same seed.
Before use, check that the 60-day sessions are a prefix of the 180-day ones
per client.

Fits: 3 seeds × 5 arms + 3 seeds × 3 reduced arms = 24.

## Metrics and analysis

Primary metric: log-loss of the predicted pass chance against pass/fail on
the test clients' tested reviews. Secondary: Brier, RMSE(bins), AUC, RMSE and
MAE against the hidden pass chance `p_pass(R_true, M)`, days metric (true
days until the hidden pass chance falls to 0.9), hold-out log-loss, and for
per-move arms RMSE of R against the hidden per-move recall.

**Bar for Q1–Q3.** For each comparison, per test client compute the mean
log-loss difference between the two arms over that client's reviews. A
difference is **established** when (a) the 95 % interval of a paired
bootstrap over clients (2,000 resamples, test clients of all three seeds
pooled) excludes 0, and (b) the per-seed differences have the same sign in
all three seeds. If (a) holds but not (b), the result is **inconclusive**.
Otherwise **no difference shown**. The bar is not changed after results.

**A1c-R.** Reported as the gap closed:
`(defaults − arm) / (defaults − A1c-R)` in test log-loss.

## Validity checks

- Every shared-trainer fit converges (`converged` true and max projected
  gradient below 1e-3). A fit that does not is reported as is and rerun with
  `maxiter` raised as a new attempt.
- Results are pulled back and the scores of every arm recomputed locally from
  the saved weights with the numpy scorer; they must match the cluster's to
  1e-9 in log-loss.
- Dataset hashes recorded in the manifests are checked after the transfer.

## Budget and stopping

At most 3 A100-hours of Slurm allocation (agreed 2026-11-16); expected well
under 1 hour. Stop when all 24 fits are scored, or before the budget would be
exceeded (then ask). Data generation and A1 run on the CPUs of the same job.

## Source and environment

Code under test is not yet committed. The run starts from commit `b854419`
plus the uncommitted change, stored as `code.diff` in this directory with new
files included. Cluster environment: Python 3.13.3 (uv), numpy 2.5.4,
pandas 3.1.1, scipy 1.18.1, torch 2.15.0 (CUDA build), fsrs 6.3.2,
pytest 9.2.0; the package tests run on the cluster before the fits.

Supporting code: one Slurm batch script in this directory (decided
2026-11-16: minimum inside the experiment; see the capability map).
