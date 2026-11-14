# FSRS training on synthetic clients

## Scope

This record owns the two implemented synthetic-client simulators, how FSRS-6
weights are trained and evaluated on them, and the results: the 1,000-client
simulator in `ml/ml_1000bots/` with its dataset `tempo_v1`, and the 300-client
simulator in the package `ml/tempo_ml/` (see
[300-client simulator and package](#300-client-simulator-and-package)). The client model and the dataset schema
are specified by the team in the
[synthetic clients record](../synthetic-clients/record.md) and the
[review dataset record](../review-dataset/record.md); this record only
states how the code follows them and where it adds to or departs from them.
The opening lines come from the [opening library](../opening-library/opening-library.md).

Status: implemented and measured on synthetic data only. The departures
listed under [implementation](#implementation) are proposals and have not
been accepted by the team (see [open questions](#open-questions)).
The results below were trained on the opening catalog before commit `5cbe0a6`
removed its short lines; retraining is planned in the
[retraining plan](retraining-plan.md).

## Implementation

Code: `ml/ml_1000bots/` (Python package `ml/ml_1000bots/tempo_sim/`). How to run it:
`ml/ml_1000bots/README.md`. Every knob is in `ml/ml_1000bots/tempo_sim/config.py`.

**Follows the team records:**

- Three benchmark archetypes (fast, balanced, diligent), one third each, with
  the trait values of the synthetic clients record, section 4.
- Hesitation time per move: `baseline_ms + lognormal(mu, sigma) × 1000 ×
  exp(beta (1 − R)) / (1 + alpha × reps)`. No depth or sharpness factor
  (deferred in the record).
- `reps`: +1 after a clean session, −2 (not below 0) after a blunder.
- Grade: any blunder → Again; otherwise the mean delay per move
  `total_time_ms / n_moves − baseline_ms` decides: < 500 ms Easy,
  500–1800 ms Good, > 1800 ms Hard.
- `reviews.csv` starts with the seven columns of the review dataset record:
  `agent_name, opening_name, review_status, t_days, grade, total_time_ms,
  accuracy`.

**Added where the records are silent:**

- Hidden memory is FSRS-6 with 21 weights per client: the defaults, w20 = the
  archetype's C, times per-client noise `exp(N(0, 0.15))`. The records give
  only F and C; F = 0.9^(−1/C) − 1 follows from C and is not a separate trait.
- Traits spread around the archetype values (`trait_jitter` 0.10).
- The app schedules with the default FSRS-6 weights (phase 1); the most
  overdue lines come first, at most 15 reviews a day.
- A Learning session is logged as `review_status = new`, grade 3, with no time.
- Extra columns in `reviews.csv`:
  - `line_id`: names are not unique (688 Lichess names have more than one
    move order), and the architecture record says the ML engine works on line
    IDs.
  - `day` and `timestamp`: training needs the order of a line's sessions.
  - `review_id`, `n_moves`, `n_correct`.
  - `baseline_ms`: the grader needs it.

**Departs from the synthetic clients record (proposal): recall per line.**
Record section 3.3 makes every move right with probability R. The code's
default `recall_mode = "line"` instead draws once against R per session:
recalled means every move is right; forgotten means one random move is a
blunder and the others are right with probability R. With this rule, pass
(grade > 1) happens exactly with probability R, so a fit can be checked
against the hidden weights. The record's rule remains available as
`recall_mode = "move"`.

Measured 2026-11-11 with `configs/recovery_test_overdue.json` (line) and
`configs/recovery_test_move.json` (move): 300 clients with one shared weight
vector, app scheduling with default weights. Raw output is in
`ml/ml_1000bots/runs/2026-11-11-first-training/recovery_tests/`.

| | line | move |
|---|---|---|
| sessions per client in 180 days | 40 | 264 |
| Again share | 22.2% | 93.0% |
| mean true R at review | 0.770 | 0.475 |
| val log-loss: fit / true weights | 0.5268 / 0.5259 | 0.1522 / 0.6371 |

With per-move recall, a line of M moves passes with probability R^M. Almost
every session becomes an Again, true memory spirals down, and the true
weights describe the data worse than a fit does. A check against the hidden
weights is then meaningless.

## Dataset tempo_v1

- Command: `python generate.py --out data/tempo_v1 --config configs/tempo_v1.json`
  (run in `ml/ml_1000bots/`).
- Content: 1,000 clients over 180 days; 300 library lines with 4–16 moves for
  the studied side; seed 7.
- Size: 121,532 rows, of which 97,605 are reviews.
- Split: 800 train / 200 val clients, split by client.
- Grade mix: Again 15.3%, Hard 10.1%, Good 59.5%, Easy 15.1%.
- Storage: `ml/ml_1000bots/data/tempo_v1/` (38 MB, in Git). Its `MANIFEST.txt` holds the
  sha256 of every file and of the producing code. Regenerating from that code reproduced all
  seven files byte for byte (checked 2026-11-12).
- Every parameter is listed in `ml/ml_1000bots/runs/2026-11-11-first-training/TRAINING_PARAMETERS.md`.

The grade mix depends strongly on the archetype through the absolute
500/1800 ms thresholds. In tempo_v1, fast clients got 42.9% Easy and no
Hard, diligent clients 25.3% Hard and 0.8% Easy, balanced clients 0.4% Hard
and 9.0% Easy; Again is 15–16% for all three.

## Training and results

The method is one global FSRS-6 fit with py-fsrs 6.3.2 `Optimizer`, default
settings, on the 800 train clients. Evaluation predicts pass (grade > 1) for
clients the fit never saw. The full report, with reproduction commands,
environment and every attempt, is
[first training run](../../../ml/ml_1000bots/runs/2026-11-11-first-training/SUMMARY.md).

| tempo_v1 val (200 clients) | log-loss | RMSE(bins) | AUC |
|---|---|---|---|
| default FSRS-6 | 0.3930 | 0.0335 | 0.670 |
| global fit | 0.3910 | 0.0201 | 0.670 |
| true weights (oracle) | 0.3849 | 0.0126 | 0.692 |

Conclusions, scoped to these synthetic clients:

1. The global fit beats the defaults. It closes 25% of the default-to-oracle
   gap on the val clients (95% bootstrap interval 11%–37%) and 48% on a
   control set of 200 new clients. Most of the gain is calibration; ranking
   (AUC) does not improve. The decay C moves from 0.15 to 0.43 (true median
   0.49).
2. About 100 clients (about 10,000 reviews) reach the plateau of the global
   fit.
3. Per-client fits do not help after 4 months of data:
   - py-fsrs returns the default weights below 512 reviews, and clients have
     about 56;
   - fitting only C per client is badly biased.
4. The fitted weights cannot recover w0, w1, w3 (every Learning session is
   logged as grade 3) or w19 (no same-day reviews); w17 and w18 only weakly.
   Single weights such as w7, w12 and w18 can be far from the truth while
   predictions stay good, because weights compensate each other.

## 300-client simulator and package

Code: `ml/tempo_ml/` (install and run: `ml/README.md`). Its hidden memory
differs from FSRS: per-line stability is multiplied after a clean session and
cut after a lapse (`simulator/memory/multiplicative.py`), each move is
recalled on its own, and a session passes only when every move is right.
Clients learn 1–3 new lines a day and are tested 3 minutes later. The
generator reads the catalog from `backend/tempo_demo.sqlite`; a line is
offered to the side of its family.

Current run: [FSRS-6 on the cleaned catalog, pass/fail vs true recall
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
   target available for real players, is enough.
3. In days to a 90% pass chance, A2 and B2 schedule a median 0.14 and
   0.10 days early, and 45–47 days early on lines whose true time is 30 days
   or more.
4. The earlier v1 weights, trained on the old catalog, score 13.1 pp on the
   same clients and a lower training loss than A2 on A2's own fit clients:
   A2's fit, started at the defaults, stopped in a worse local optimum.

Not accepted by the team: which weights the app ships; `backend/fitted_global.csv`
still holds the `ml_1000bots` first-run weights.

## Limits

- The hidden memory is FSRS-6 itself, so the model fits perfectly by
  construction and the results are optimistic. Real players are not FSRS-6.
- The fitted weights describe synthetic clients. They show that the method
  works and must not ship as real-player weights; retrain on real data.
  `backend/fitted_global.csv`, read by the web and terminal demos, is a byte-identical
  copy of these weights (checked 2026-11-12).
- The size of the gain depends on how far the synthetic population sits from
  the defaults, which is set by the archetype C values.

## Open questions

- Does the team accept recall per line (`recall_mode = "line"`) instead of
  per move in the synthetic clients record, section 3.3?
- Does the review dataset schema gain `line_id`, `day` (or a timestamp) and
  `baseline_ms`?
- Proposals for the ML engine, not accepted:
  - start with one global fit;
  - retrain on real data at about 100 players;
  - leave per-player fitting until players have several hundred reviews;
  - log a quality signal for Learning sessions so that w0–w3 can be learned.
