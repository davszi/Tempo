# Experiment: line-level versus per-move FSRS under the decided grading rule

Protocol, fixed before the run: [PLAN.md](PLAN.md). Decisions behind it:
[move recall record](../../../docs/topics/move-recall/move-recall.md) and
[training approaches](../../../docs/topics/move-recall/approaches.md).
Run on 2026-11-16; this record written on 2026-11-17.

**Kind.** Investigation; Q1–Q3 confirmatory with the bar in PLAN.md, the
rest exploratory. **Everything here is simulated players**; nothing is
measured on people.

## Results

Test clients of the three populations (seeds 20261111, 20261121, 20261131),
22,851 scored reviews, 92.7% passed; hold-out: 180 new clients, 22,703
reviews. Log-loss of the predicted pass chance, lower is better, mean over
the seeds ([results/tables.md](results/tables.md),
[results/scores.json](results/scores.json)):

| Arm | Test | Hold-out | RMSE vs hidden pass chance | AUC | Median abs. days error |
|---|---|---|---|---|---|
| Untrained (FSRS-6 defaults) | 0.2123 | 0.2202 | 0.0773 | 0.832 | 6.42 |
| A1, py-fsrs, line | 0.2033 | 0.2115 | 0.0642 | 0.836 | 8.47 |
| A1c, line | 0.2029 | 0.2112 | 0.0628 | 0.835 | 11.48 |
| A1c-pass, per move | 0.1902 | 0.1980 | 0.0415 | 0.868 | 5.53 |
| A1c-acc, per move | 0.1900 | 0.1982 | 0.0417 | 0.868 | 5.75 |
| A1c-R, per move, hidden truth (reference) | 0.1898 | 0.1982 | 0.0405 | 0.868 | 6.05 |
| Perfect (hidden pass chance) | 0.1848 | 0.1910 | 0 | 0.878 | — |

**Verdicts (bar of PLAN.md).**

| Question | Comparison | Change in test log-loss (b − a) | 95 % interval | Per seed | Verdict |
|---|---|---|---|---|---|
| Q1 meaning of R | A1c → A1c-pass | −0.0121 | [−0.0143, −0.0099] | −0.0129, −0.0125, −0.0107 | established |
| Q2 training target | A1c-pass → A1c-acc | −0.0002 | [−0.0004, +0.0001] | −0.0003, −0.0003, +0.0000 | no difference shown |
| Q2, first 60 days only | A1c-pass → A1c-acc | −0.0000 | [−0.0004, +0.0003] | +0.0003, −0.0006, +0.0001 | no difference shown |
| Q3 trainer | A1 → A1c | −0.0003 | [−0.0006, −0.0000] | −0.0003, −0.0007, +0.0001 | inconclusive |

What they establish, on these simulated players:

1. **Per-move recall predicts the pass outcome better than line-level
   recall** (Q1), in all three populations and on hold-out. Against the
   perfect predictor, the line-level arms close 33–34 % of the gap from the
   defaults and the per-move arms 80–81 % (hold-out 30–31 % and 75–76 %). The
   rest is player variation: every simulated player has its own 21 weights,
   and one shared set cannot match them all.
2. **The two per-move targets are equivalent here** (Q2), also with a third
   of the history. The expectation recorded in
   [training approaches, section 6](../../../docs/topics/move-recall/approaches.md#6-expectations-and-how-they-are-tested),
   that the accuracy target would fit better and more so with less data, was
   not borne out.
3. **Trainer:** a difference of 0.0003 whose sign changes between seeds;
   inconclusive by the bar and small in any case.

**By line length** (test clients, all seeds; [tables.md](results/tables.md)):
the line-level model predicts one pass rate for every length (A1c: 81 % on
3-move lines, 94–96 % on 4–5), while the observed rate jumps where one more
mistake is allowed (73 % at 3 moves, 98 % at 4). The per-move arms follow
the observed rate (A1c-pass 72 % and 98 %).

**Timing.** Median absolute error of the days until the pass chance falls
to 0.9: per-move arms 5.5–5.8 days, A1 8.5, A1c 11.5, the untrained defaults
6.4. Training a line-level model lowers its log-loss but worsens its timing;
the per-move arms improve both. Median signed error: A1c-pass +0.25 days,
A1c +3.4.

**Gap closed on the planned scale.** PLAN.md defined the gap against A1c-R.
On that scale A1c-pass reaches 98.4 % on test and 100.8 % on hold-out:
A1c-R is trained on the hidden per-move recall, not on the pass outcome, so
it is not a ceiling. The record and the explainer page therefore also use
the perfect predictor; both scales are in [tables.md](results/tables.md).

## Arms, data and settings

As in PLAN.md: FSRS-6 hidden memory, the decided grading rule, the current
catalog (2,719 lines), app clock, split by archetype (seed 7), start at the
FSRS-6 defaults, personalisation skipped. 300 clients per population over
180 days; hold-out 60 per population; reduced data = the first 60 days,
checked to be a per-client prefix of the full data. Datasets, their hashes
and how to regenerate them: [dataset_MANIFEST.txt](dataset_MANIFEST.txt).

All 21 shared-trainer fits converged (`CONVERGENCE: RELATIVE REDUCTION OF F <= FACTR*EPSMCH`;
107–1,041 iterations; largest projected gradient 5.9e-4, below the 1e-3 bar;
17–322 s each on the A100). A1 took 147–156 s per seed on CPU.

## Attempts

| # | What | Outcome |
|---|---|---|
| 1 | Slurm job 39789 (`run.sbatch`, one A100 80GB, 8 CPUs, 32 GB, cloud-206), 47 min 12 s | 85 package tests passed on the node; 9 datasets generated; 21 shared-trainer fits converged. **A1 failed** (`ModuleNotFoundError: No module named 'tempo_ml'`: the script runs as a file and the package was not installed); the closing comparison failed the same way, so the job ended FAILED (exit 1) |
| 2 | Job 39793, CPU, A1 with `PYTHONPATH` set, 3 s | **Failed:** py-fsrs's Optimizer needs its `optimizer` extra (`tqdm` was missing on the cluster). The A1 logs of attempts 1–2 were overwritten by attempt 3; the failure lines survive in `results/logs/slurm-39793-A1.out` and in this record |
| 3 | `tqdm==4.70.1` installed (the local version); job 39797, CPU, 2 min 40 s | A1 succeeded for all seeds |
| 4 | Job 39800, CPU, `compare.py` version 1, 8 s | Succeeded; output kept unchanged in `results/compare-v1-cluster/` |
| 5 | Local (macOS), 2026-11-16 | Results and data copied back; 45 dataset hashes matched; all scores recomputed from the saved weights matched the cluster within 6e-17; seed 20261111 train regenerated byte for byte |
| 6 | Local, 2026-11-17, after merging `7ef4fe7` | The merge replaced the simulator's grading function with the identical rule of `52e9535`; all nine datasets regenerated byte for byte with the merged code |
| 7 | Local, 2026-11-17, `compare.py` version 2 | Adds the perfect predictor, both gap scales and pass rate by line length; the 2,208 numbers version 1 wrote agree within 2e-11 (cluster and macOS floating point). Version 2 output is `results/scores.json` and `results/tables.md` |

Running totals (supporting code: `run.sbatch` plus the three one-line
`--wrap` commands of jobs 39793, 39797 and 39800; counted with `wc -l`;
the experiment's own scripts `compare.py` and `train_pyfsrs.py` are not
supporting code):

- Total after attempt 1: 1 attempt, 0 usable results (A1 and the comparison missing), 69 lines of supporting code and 0 lines of tests, the person's minutes not recorded.
- Total after attempt 2: 2 attempts, 0 usable results, 71 lines of supporting code and 0 lines of tests, the person's minutes not recorded.
- Total after attempt 3: 3 attempts, 1 usable result (all fits), 72 lines of supporting code and 0 lines of tests, the person's minutes not recorded.
- Total after attempt 4: 4 attempts, 2 usable results, 73 lines of supporting code and 0 lines of tests, the person's minutes not recorded.

Changed settings during the run, with reasons: `PYTHONPATH` added to
`run.sbatch` (attempt 1); `fsrs[optimizer]` declared in `ml/pyproject.toml`
and `tqdm` installed on the cluster (attempt 2); `compare.py` extended after
the run (attempt 7), not changing any planned number.

## Source and environment

The run started from commit `b854419` plus the uncommitted change in
[code.diff](code.diff) (new files included), which is the code these
results come from. That change lands in the repository after merging
`7ef4fe7`, where the simulator's grading function is the app team's
identical implementation (`calculate_session_grade`, `52e9535`); attempt 6
shows the merged code produces the same data, and the trainer and scorer
are unchanged by the merge.

Cluster: TU Clausthal Slurm, partition `batch`; Python 3.13.3 (uv), numpy
2.5.4, pandas 3.1.1, scipy 1.18.1, torch 2.15.0+cu132 (CUDA 13.2, driver
580.196.07), fsrs 6.3.2, tqdm 4.70.1, pytest 9.2.0. Local checks: the same
versions on macOS. Resource use: one A100 for 47 min 12 s (0.8 of the agreed
3 A100-hours) plus 2 min 51 s of CPU-only jobs.

Reproduction, from `ml/` with that environment:

```bash
sbatch experiments/2026-11-16-move-recall/run.sbatch            # or run its commands by hand
python experiments/2026-11-16-move-recall/compare.py --data data/move-recall \
    --results experiments/2026-11-16-move-recall/results --out experiments/2026-11-16-move-recall/results
```

`run.sbatch` exports `PYTHONPATH`, so A1 and the comparison run inside the
job; attempts 2–4 show the separate commands that were actually used.

## Run output

Tracked here: `results/` (per seed and arm `fsrs6_general_parameters.json`
and `metrics.json`, the comparison outputs of both versions, and all logs).
Not tracked: the datasets (17 MB), listed with hashes in
[dataset_MANIFEST.txt](dataset_MANIFEST.txt). **Open: whether they stay
outside Git is the person's decision, asked on 2026-11-17 and not yet
answered;** until then this experiment is not complete.

Cluster copies owned by this run, not yet cleaned up (deletion needs the
person's approval): `~/tempo-move-recall/` on cloud-201 (3.1 GB, mostly the
Python environment, plus the datasets and results).

## Limits

- Simulated players only. Moves are recalled independently by construction,
  so `p_pass` is exact here; whether real players' mistakes cluster, and
  which per-move target then suits them, is open
  ([move recall record, section 7.3](../../../docs/topics/move-recall/move-recall.md#73-checking-the-binomial-assumption-on-real-reviews)).
- One shared set of weights per arm; personalisation was not run.
- The app schedules on line-level recall; the per-move weights need the
  per-length scheduler before they could ship (move recall record, section 3.3).
- Days results use the pass-chance definition of 2026-11-16 and are not
  comparable with the 2026-11-13 and 2026-11-14 experiments.
- The A1 logs of the failed attempts were overwritten (attempt 2).

## Next

The team decision on which weights ship (move recall record, section 7.4)
and the app's per-length scheduler. This is the third finished experiment
(2026-11-13, 2026-11-14, 2026-11-16): the kit's step-back review across
experiments is due, pending the person's go-ahead.
