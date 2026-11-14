# Experiment: FSRS-6 on the cleaned opening catalog, pass/fail vs true recall (v2)

Arms A2 and B2 of the [retraining plan](../../../docs/topics/fsrs-training/retraining-plan.md),
run on the 300-client simulator (multiplicative memory, every move must be
right). Topic record: [FSRS training](../../../docs/topics/fsrs-training/fsrs-training.md).
The 1000-agent arms (A1, A1c, B1) are not part of this run.

## Protocol (from the plan, fixed before the run)

**Questions.** (1) Do FSRS-6 weights trained on pass/fail still beat the
defaults on the cleaned catalog, in percentage points of recall and in days?
(2) How much closer do the weights get when trained on the hidden true chance
of a clean session instead of pass/fail?

**Kind.** Exploratory investigation; no pass/fail bar.

**Arms.** Same data, same split, same optimizer (L-BFGS-B within the FSRS-6
bounds, finite-difference gradients, start at the defaults, `maxiter=300`):

| Arm | Target | Loss | Output |
|---|---|---|---|
| A2 | pass (grade > 1) | log-loss | `results/binary/` |
| B2 | `p_clean` from `ground_truth.csv`, fit clients only | MSE | `results/true-recall/` |

B2 is a diagnostic: real players have no `p_clean`.

**Baselines.** FSRS-6 default weights; a constant equal to the fit clients'
pass rate. There is no oracle: the hidden memory is not FSRS.

**Evaluation.** 60 test clients (split by archetype, seed 7) and 60 new
hold-out clients (seed 20261112). Metrics: log-loss, Brier, RMSE(bins), AUC,
RMSE and MAE against `p_clean`, and the days metric (predicted minus true days
until the chance of a clean session drops to 90%; definition in the plan).
Per-player fine-tuning is skipped (`--no-personalise`).

## Inputs, code and environment

- Opening catalog: `backend/tempo_demo.sqlite` as of commit `09f8a22`
  (tables `opening_lines`, `opening_families`; 91 families, 2,719 lines),
  content sha256 `00a697c2…`. Families are drawn uniformly: the catalog has
  no family popularity (plan, open questions). The catalog was regrouped
  later (`d2e5903`, 82 families); these results use the earlier grouping.
- Data (git-ignored, in `ml/data/fsrs-synthetic-v2/`; location, hashes and
  the verified byte-for-byte regeneration in
  [`dataset_MANIFEST.txt`](dataset_MANIFEST.txt)):
  - `train/`: 300 clients, 131,981 sessions (8,090 Learning, 123,891
    Repeating), 101,090 tested reviews; split fit 210 / validation 30 /
    test 60 clients (71,751 / 8,836 / 20,503 reviews).
  - `holdout/`: 60 clients, 26,444 sessions, 20,269 tested reviews.
- Source: commit `09f8a22` plus the uncommitted changes in
  [`code.diff`](code.diff) (catalog reader, metrics, `--target`,
  `--no-personalise`), run in the earlier layout
  `ml/ml_300bots/ml_engine/src/tempo_ml/`. The same code now lives in
  `ml/tempo_ml/`, reorganised without changing behaviour (simulator split
  into `clients`, `recall`, `practice`, `grading`, `generate`; metrics into
  `evaluate/metrics.py` and `evaluate/days.py`) plus the catalog change above.
  Checked after the reorganisation: a test dataset is byte-identical before
  and after it, and rerunning `compare_v1.py` and `holdout_benchmark.py`
  reproduced `v1_comparison.json` and `holdout_benchmark.json` exactly. Raw
  outputs keep the old paths they were written with.
- Environment: Python 3.13.5, numpy 2.5.4, scipy 1.18.1, pandas 3.1.1,
  Windows 11, run on a laptop. Generation took 4.4 s and 1.1 s; A2 trained in
  183 s, B2 in 418 s, run in parallel.
- Checks: the test suite passed (42 tests, 7 of them new).

## Reproduce

Data: see [`dataset_MANIFEST.txt`](dataset_MANIFEST.txt); the generation
settings are also in `ml/configs/multiplicative-memory.json` and
`multiplicative-memory-holdout.json` (they rebuild these bytes only with the
catalog and code of `09f8a22`, see the manifest). Training and scoring, from
`ml/` after `pip install -e ".[train,test]"`, in the current layout
(E = `experiments/2026-11-13-fsrs-synthetic-v2`, D = `data/fsrs-synthetic-v2`):

```bash
python -m tempo_ml.fsrs.train --data D/train --out E/results/binary --seed 7 --target pass --no-personalise
python -m tempo_ml.fsrs.train --data D/train --out E/results/true-recall --seed 7 --target true --no-personalise
python E/holdout_benchmark.py --data D/holdout --weights A2_pass=E/results/binary/fsrs6_general_parameters.json B2_true=E/results/true-recall/fsrs6_general_parameters.json --base-rate 0.5814692478153615 --out E/results/holdout_benchmark.json
python E/compare_v1.py
python E/benchmark_data.py
```

Raw outputs in `results/`: `binary/` and `true-recall/` (each
`fsrs6_general_parameters.json`, `metrics.json`, `train.log`),
`holdout_benchmark.json`, `v1_comparison.json`; all of them collected in one
file: [`results/benchmark-data.md`](results/benchmark-data.md). The
step-by-step page for people is [`walkthrough.html`](walkthrough.html).

## Results

**Optimizer.** A2 converged after 90 iterations (fit log-loss 0.5602). B2
stopped at the 300-iteration limit without meeting the convergence test (fit
MSE 0.0177). The limit is the plan's setting and was not changed after seeing
results; a run with a higher limit would be a new attempt.

**Test clients (60 clients, 20,503 reviews, observed pass rate 58.2%).**

| Predictor | Log-loss | Brier | RMSE(bins) | AUC | RMSE vs truth | MAE vs truth | Mean prediction |
|---|---|---|---|---|---|---|---|
| Constant (58.1%) | 0.680 | 0.243 | 0.0 pp | 0.500 | 27.0 pp | 23.0 pp | 58.1% |
| FSRS-6 default | 0.723 | 0.246 | 19.2 pp | 0.701 | 27.7 pp | 21.9 pp | 76.9% |
| A2, pass/fail | 0.562 | 0.189 | 2.6 pp | 0.774 | 14.1 pp | 10.6 pp | 58.6% |
| B2, true recall | **0.560** | **0.189** | **2.1 pp** | **0.775** | **13.8 pp** | **10.4 pp** | 58.5% |

**Hold-out clients (60 new clients, 20,269 reviews, observed 57.9%).**

| Predictor | Log-loss | Brier | RMSE(bins) | AUC | RMSE vs truth | MAE vs truth | Mean prediction |
|---|---|---|---|---|---|---|---|
| Constant (58.1%) | 0.681 | 0.244 | 0.3 pp | 0.500 | 26.6 pp | 22.7 pp | 58.1% |
| FSRS-6 default | 0.735 | 0.251 | 19.5 pp | 0.692 | 27.7 pp | 22.0 pp | 76.9% |
| A2, pass/fail | 0.570 | 0.193 | 3.1 pp | 0.768 | 13.8 pp | 10.5 pp | 58.4% |
| B2, true recall | **0.568** | **0.192** | **2.6 pp** | **0.769** | **13.5 pp** | **10.3 pp** | 58.3% |

**Days metric, test clients (26,763 sessions; median true time to 90% is
0.57 days; 486 sessions have a true time beyond the 180-day horizon).**
Negative = the review would come too early.

| Predictor | Median error | Median abs error | Median rel. error | Too early | Mean error |
|---|---|---|---|---|---|
| FSRS-6 default | +0.00 d | 1.12 d | +1% | 50% | −2.4 d |
| A2, pass/fail | −0.14 d | 0.24 d | −49% | 82% | −11.7 d |
| B2, true recall | −0.10 d | 0.22 d | −39% | 77% | −11.2 d |

By true interval (median error, median relative error):

| True days to 90% | Sessions | Default | A2 | B2 |
|---|---|---|---|---|
| under 7 | 21,185 | +0.08 d (+23%) | −0.10 d (−46%) | −0.07 d (−34%) |
| 7–30 | 2,975 | −3.4 d (−30%) | −5.2 d (−46%) | −4.8 d (−43%) |
| 30 or more | 2,603 | −38.6 d (−68%) | −47.0 d (−74%) | −45.0 d (−72%) |

After a Learning session the default model is 2.1 days late (median), A2 and
B2 0.1 days early. The hold-out clients give the same picture (default
+0.00 d, A2 −0.14 d, B2 −0.11 d median; `results/holdout_benchmark.json`).

**By archetype (test, RMSE vs truth).** Balanced: default 26.0, A2 11.8,
B2 11.5 pp. Blitzer: 31.4, 17.2, 16.9 pp. Diligent: 24.5, 12.2, 12.0 pp.

**Fitted weights.** Decay `w20`: default 0.154, A2 0.510, B2 0.715. Several
weights sit on a bound in both arms (`w9` = 0, `w13` = 0.9, `w15` and
`w16` = 1.0), and A2 and B2 differ strongly in `w8`, `w10` and `w12` while
predicting almost the same; weights compensate each other.

## Interpretation

1. **Training still pays off on the cleaned catalog.** Against the defaults,
   A2 halves the error against the true chance (27.7 → 14.1 pp), removes
   most of the calibration error (19.2 → 2.6 pp) and ranks better (AUC 0.70
   → 0.77), on test and hold-out clients alike.
2. **Perfect labels add little.** B2, trained on the hidden truth, is only
   0.2–0.3 pp closer to the truth than A2. The remaining 13.5–14 pp is the
   gap between FSRS-6 with one global weight set and this simulator's
   memory (per-move recall, a clean session needs all moves, per-client
   decay), not noise in the pass/fail labels. Richer labels would not fix
   it; a model closer to the memory or per-player parameters might.
3. **In days, the trained models schedule early.** Most sessions have a very
   short true time to 90% (median 0.57 d: a clean run of a long line drops
   below 90% quickly), and both trained models predict about half of it.
   On lines whose true time is 30 days or more they are 45–47 days early,
   worse than the defaults. Early is the safe direction (more reviews, no
   extra forgetting), but the scheduler would over-review strong lines.
   The days metric measures the curve near 90%, where few reviews happen;
   the probability metrics measure it near the observed 58%.

## Comparison with the v1 weights (added after the run)

Question asked after the results: how do the v1 weights (trained on the old
catalog; folder removed, retrievable at commit `09f8a22`, weights also stored in
`results/v1_comparison.json`) fare on these clients? No fitting; all four
weight sets scored on the same v2 test and hold-out clients with the same
`score()` as training ([`compare_v1.py`](compare_v1.py), output
`results/v1_comparison.json`).

| Test clients (60) | Defaults | v1 | A2 | B2 |
|---|---|---|---|---|
| RMSE vs true chance | 27.7 pp | 13.1 pp | 14.1 pp | 13.8 pp |
| RMSE(bins) calibration | 19.2 pp | 4.1 pp | 2.6 pp | 2.1 pp |
| AUC | 0.701 | 0.785 | 0.774 | 0.775 |
| Mean prediction (observed 58.2%) | 76.9% | 59.9% | 58.6% | 58.5% |
| Log-loss | 0.7231 | 0.5516 | 0.5620 | 0.5603 |
| Days, median error | +0.00 d | −0.17 d | −0.14 d | −0.10 d |
| Days, share too early | 50% | 86% | 82% | 77% |
| Days, lines with true time ≥ 30 d | −38.6 d | −40.9 d | −47.0 d | −45.0 d |

Hold-out clients agree (v1 13.2 pp, A2 13.8 pp, B2 13.5 pp; calibration
4.6 / 3.1 / 2.6 pp). On A2's own fit clients the v1 weights also reach a
lower log-loss than A2 (0.5532 vs 0.5602), so A2's L-BFGS-B run, started at
the defaults, stopped in a worse local optimum; the v1 weights are a better
point of the same objective. A2 stays better calibrated and slightly less
early in days. A run of A2 started from the v1 weights (or several starts,
best on validation) would be a new, recorded attempt; it was not run.

## Caveats

- Synthetic clients from one generator and one seed per dataset.
- B2 did not converge within the 300-iteration limit.
- Family choice is uniform, unlike v1 (popularity-weighted), so v1 and v2
  numbers are not directly comparable. The v1 folder was removed on
  2026-11-13 (retrievable at `09f8a22`).
- The FSRS-6 card is a whole line while the hidden memory is per move; the
  days metric therefore compares two different curve shapes.
