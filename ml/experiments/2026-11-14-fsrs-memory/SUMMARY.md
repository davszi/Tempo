# Experiment: FSRS-6 on clients whose hidden memory is FSRS-6 (arms A1, A1c, B1)

Arms A1, A1c and B1 of the [retraining plan](../../../docs/topics/fsrs-training/retraining-plan.md),
run on the package simulator of `ml/tempo_ml/` with the new FSRS-6 hidden
memory model (`simulator/memory/fsrs.py`). Everything else (clients, sides,
repertoires, per-move recall with retries, grading, practice policy, split,
trainer, metrics) is the code and configuration of arms A2 and B2
([2026-11-13-fsrs-synthetic-v2](../2026-11-13-fsrs-synthetic-v2/SUMMARY.md)),
so the two experiments differ in the hidden memory model. Topic record:
[FSRS training](../../../docs/topics/fsrs-training/fsrs-training.md).

## Protocol

**Questions.** (1) When the clients' memory follows FSRS-6 itself, does a
global FSRS-6 fit on pass/fail beat the defaults, and by how much of the gap
to a perfect predictor? (2) Does training on the hidden true chance of a
clean session (B1) add anything over pass/fail (A1c), with the same trainer?
(3) Does the official py-fsrs optimizer (A1) differ from the shared trainer
(A1c)?

**Kind.** Exploratory investigation; no pass/fail bar. The arms, split,
metrics and trainer settings were fixed by the retraining plan and the A2/B2
run before this run; the clock comparison in the results was added after A1
was first scored (see [attempts](#attempts-and-changes)).

**Decision it informs.** Whether the pass/fail target that real players can
supply is enough, and which trainer the app should use.

**Arms.** Same data and split; all start at the FSRS-6 defaults.

| Arm | Trainer | Target | Loss | Output |
|---|---|---|---|---|
| A1 | py-fsrs 6.3.2 `Optimizer`, default settings (Adam, lr 0.04, 5 epochs, batch 512) | pass (grade > 1) | log-loss | `results/pyfsrs/` |
| A1c | `tempo_ml.fsrs.train` (L-BFGS-B within the FSRS-6 bounds, finite differences, `maxiter=300`, default tolerances) | pass (grade > 1) | log-loss | `results/binary/` |
| B1 | as A1c | `p_clean` from `ground_truth.csv`, fit clients only | MSE | `results/true-recall/` |

B1 is a diagnostic: real players have no `p_clean`. A1c and B1 use exactly
the settings of A2 and B2, including scipy's default stopping tolerances.

**Baselines.** FSRS-6 default weights; a constant equal to the fit clients'
pass rate; a perfect predictor that outputs the hidden `p_clean`.

**Evaluation.** 60 test clients (split by archetype, seed 7) and 60 new
hold-out clients (seed 20261112), scored with `tempo_ml.evaluate.metrics.score`
on tested reviews at least one day after the previous session: log-loss,
Brier, RMSE(bins), AUC, RMSE and MAE against `p_clean`, and the days metric.
Paired 95% intervals: 1,000 resamples of whole clients (`score_all.py`).
Elapsed time is the exact `t_days` (the clock of the shared trainer and of
A2/B2); the same metrics with calendar days are reported beside them.

**Budget and stopping.** One run of each arm; about 10 minutes on one machine.

## Inputs, code and environment

- Opening catalog: `backend/tempo_demo.sqlite` as maintained by the team
  ([opening catalog structure](../../../docs/topics/opening-catalog/opening-catalog.md)),
  as of commit `825e9d8`: 82 families, 2,719 lines, content sha256
  `da5fc96c…` (full value in [`dataset_MANIFEST.txt`](dataset_MANIFEST.txt)).
- Configs: `ml/configs/fsrs-memory.json` and `fsrs-memory-holdout.json`, the
  multiplicative configs plus `"memory": "fsrs"`.
- Data (git-ignored, `ml/data/fsrs-memory/`; hashes and regeneration in
  [`dataset_MANIFEST.txt`](dataset_MANIFEST.txt)):
  - `train/`: 300 clients, 283,149 sessions, 216,271 tested reviews; fit 210
    clients (149,972 reviews), validation 30 (unused), test 60 (44,560).
  - `holdout/`: 60 clients, 58,480 sessions, 44,484 tested reviews.
  - `clients.csv` and `repertoires.csv` are byte-identical to those of the
    multiplicative configs on the same catalog: the clients' traits, sides and
    lines are the same; only the hidden memory differs.
- FSRS-6 memory: each client's 21 weights are the FSRS-6 defaults with
  log-normal noise (sd 0.15) on w0–w16, w17–w19 at the defaults, w0–w3
  sorted, w20 set to the client's decay C, clipped to the FSRS-6 bounds,
  drawn from their own random stream. Stability and difficulty follow the
  graded FSRS-6 update; after a lapse the stability stays at least 1 day,
  as in the multiplicative model.
- Source: this experiment's landing commit. Checked before landing: a clean
  checkout of `825e9d8` with exactly these changes regenerated both datasets
  byte for byte and reproduced the three weight files and `scores.json`
  exactly. The multiplicative model is unchanged by it: with
  `configs/multiplicative-memory*.json` the generator writes the same eight
  CSV files, byte for byte, before and after the change.
- Scripts here: `train_pyfsrs.py` (arm A1), `score_all.py` (every score and
  interval), `tables.py` (writes `results/tables.md`).
- Environment: Python 3.13.3, numpy 2.5.4, pandas 3.1.1, scipy 1.18.1,
  fsrs 6.3.2, torch 2.15.0, macOS 15.5, Apple M4.

## Results

Full tables, both clocks and both client sets: [`results/tables.md`](results/tables.md);
raw values: `results/scores.json`, `results/*/metrics.json`.

**Test clients, exact clock** (observed pass rate 38.4%):

| Weights | Log-loss | RMSE(bins) pp | AUC | RMSE vs truth pp | Mean predicted | Gap closed |
|---|---:|---:|---:|---:|---:|---:|
| Constant | 0.6661 | 0.7 | 0.500 | 20.1 | 39.1% | |
| FSRS-6 defaults | 0.8307 | 29.9 | 0.669 | 32.5 | 67.7% | 0% |
| A1 | 0.7135 | 18.1 | 0.618 | 24.7 | 54.8% | 46% |
| A1c | 0.6084 | 2.3 | 0.692 | 12.2 | 38.9% | 86% |
| B1 | 0.6091 | 2.5 | 0.691 | 12.3 | 39.2% | 86% |
| Perfect (`p_clean`) | 0.5735 | | | 0 | | 100% |

Gap closed = (defaults − arm) / (defaults − perfect), in log-loss. Hold-out
clients agree: defaults 0.8330, A1 0.7254, A1c 0.6101, B1 0.6107.

1. **Training fixes a large overestimate.** The defaults predict 67.7%
   where 38.4% of reviews pass, and score worse than the constant. A1c and B1
   predict within 1 pp of the observed rate and close 86% of the gap.
2. **The true-chance target adds nothing.** B1 against A1c: −0.0008 log-loss
   (95% interval −0.0012 to −0.0004) on test clients, −0.0006 on hold-out
   clients. B1 is slightly worse, not better.
3. **A1 trails only because of the clock.** py-fsrs counts whole calendar
   days. Scored on calendar days, A1 reaches 0.6127 and A1c 0.6117 (A1c − A1
   gain +0.0010, interval −0.0006 to +0.0028); on hold-out clients A1 is
   ahead (0.6133 vs 0.6145). The trainer does not matter; the clock used
   for training and for scheduling must be the same.
4. **Days.** Trained weights call about 89% of reviews early (defaults 49%).
   On lines whose true time to a 90% pass chance is 30 days or more, the
   median error is −21.0 days for A1c, −10.8 for B1 and −18.0 for A1; the
   defaults are 236 days late there.

**Fitted decay C** (w20): A1 0.499, A1c 0.591, B1 0.563; the clients' true
median 0.500, the default 0.154.

**Optimizer.** A1c stopped at the 300-iteration limit without converging
(412 s); B1 converged after 242 iterations (322 s); A1 took 219 s including
data preparation.

## Attempts and changes

- A1 was first scored only on exact time (0.7135) and looked far worse than
  A1c. Because py-fsrs trains on calendar days, every arm was then also
  scored on calendar days (`score_all.py`); both clocks are reported.
- Before this run, the same question was explored in the separate
  1,000-client simulator `ml/ml_1000bots/` (removed on 2026-11-14; its last
  committed state is at `825e9d8`). That simulator decided recall once per
  line. Its exploratory variants, none committed:
  - per-move recall alone: lines locked up (6% pass, 92% relearning
    sessions) because a lapse could drive the FSRS stability to 0.01 days;
    a 1-day lapse floor, as in the multiplicative model, removed this;
  - a re-implementation of the A2/B2 practice policy with FSRS memory:
    37% pass, A1c and B1 gap closed 85–86%, B1 no better than A1c; rerun on
    a second machine, A1 was identical while A1c and B1 reached different
    weights with log-loss within 0.0003;
  - the same policy with recall once per line: 92% pass, and no arm beat
    the defaults (the defaults were within 0.003 log-loss of perfect).
  That re-implementation drew opening families by popularity, unlike the
  package, so it is superseded by this run, which uses the package itself.
  Its code and outputs are not kept in the repository.

## Caveats

- The hidden memory is FSRS-6 for each move, so FSRS-6 is correctly specified
  per move but not per line: a line passes with probability R^M.
- A1c did not converge within 300 iterations, and A2 stopped early in its
  own run; stricter tolerances might change A1c and A2 slightly.
- One run per arm. In the earlier exploration, rerunning A1c and B1 on a
  second machine moved their log-loss by up to 0.0003, so smaller
  differences between arms are not meaningful.
- Synthetic clients only. Which memory model resembles real players is
  open.
- The A2/B2 record states its own catalog version; compare the two memory
  models with that in mind.

## Reproduction

From this experiment's landing commit, in `ml/` with `pip install -e ".[train,test]"`,
`fsrs[optimizer]==6.3.2` and `torch==2.15.0`:

```bash
python -m tempo_ml.simulator.generate --config configs/fsrs-memory.json --out data/fsrs-memory/train
python -m tempo_ml.simulator.generate --config configs/fsrs-memory-holdout.json --out data/fsrs-memory/holdout
E=experiments/2026-11-14-fsrs-memory
python -m tempo_ml.fsrs.train --data data/fsrs-memory/train --out $E/results/binary --seed 7 --target pass --no-personalise
python -m tempo_ml.fsrs.train --data data/fsrs-memory/train --out $E/results/true-recall --seed 7 --target true --no-personalise
python $E/train_pyfsrs.py --data data/fsrs-memory/train --out $E/results/pyfsrs --seed 7
python $E/score_all.py --train data/fsrs-memory/train --holdout data/fsrs-memory/holdout --results $E/results
python $E/tables.py $E/results
```
