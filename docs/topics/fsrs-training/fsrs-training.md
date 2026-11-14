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
| `multiplicative` (default) | `simulator/memory/multiplicative.py` | decay C | stability × (1 + 1.5·e^(2(1−R))) | stability × 0.3, at least 1 day |
| `fsrs` | `simulator/memory/fsrs.py` | 21 FSRS-6 weights, w20 = C | FSRS-6 recall update with the line's difficulty | FSRS-6 forget update, at least 1 day |

Both use the forgetting curve of the synthetic clients record, section 3.2.
The FSRS-6 weights are the defaults with log-normal noise (sd 0.15) on w0–w16,
w17–w19 at the defaults, drawn from their own random stream; with the same
config apart from `memory`, both models give the same clients, sides and
repertoires. Selecting `fsrs` leaves the multiplicative model unchanged: its
generator output is byte-identical before and after `fsrs` was added.

## Multiplicative memory: arms A2 and B2

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
   (interval includes zero). The trainer does not matter; training and
   scheduling must use the same clock.
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

- Synthetic clients only. Under FSRS memory the model is correctly specified
  per move, so those results are optimistic; under multiplicative memory it
  is not FSRS at all. Which resembles real players is open.
- Trained weights describe synthetic clients. They show that the method
  works and must not ship as real-player weights; retrain on real data.
- The size of the gain depends on how far the synthetic population sits from
  the defaults.

Not accepted by the team: which weights the app ships; `backend/fitted_global.csv`
still holds the first-run weights of the removed simulator.
