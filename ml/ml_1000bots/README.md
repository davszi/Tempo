# tempo_sim

Synthetic chess players for TEMPO: generates practice histories, trains FSRS-6
weights on them and scores the result against the players' hidden true weights.

- What the simulator does, how it follows the team records, and the results:
  [FSRS training on synthetic clients](../docs/topics/fsrs-training/fsrs-training.md)
- Opening lines and their White/Black classification:
  [opening library](../docs/topics/opening-library/opening-library.md)

## Install

Python 3.13 (3.12 should work).

```bash
cd ml
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m pytest tests/      # FSRS-6 implementation == py-fsrs 6.3.2 (21 tests)
```

## Run

```bash
python generate.py --out data/tempo_v1 --config configs/tempo_v1.json   # dataset, ~5 s
python report.py data/tempo_v1                                          # report.png + report.md
python fit_global.py data/tempo_v1 runs/2026-11-11-first-training   # one global fit, ~100 s
```

The experiment scripts in `experiments/` and their commands are listed in
[`runs/2026-11-11-first-training/SUMMARY.md`](runs/2026-11-11-first-training/SUMMARY.md).

## Layout

| Path | Content |
|---|---|
| `tempo_sim/` | the package: `config.py` (every knob), `persona.py`, `play.py`, `simulate.py`, `fsrs6.py`, `evaluate.py` |
| `generate.py`, `report.py`, `fit_global.py` | dataset generation, sanity report, global fit |
| `configs/` | `tempo_v1.json` (final dataset) and recovery tests with one known weight vector |
| `experiments/` | agent-count curve, per-player fits, analysis, control benchmark, recall-mode stats |
| `openings/` | opening library and the scripts that classify it |
| `runs/` | one folder per training run: parameters, results, raw outputs |
| `data/` | generated datasets; only `data/tempo_v1/` (the first run's dataset) is in Git, regenerate others with `generate.py` |
| `tests/` | FSRS-6 implementation checked against py-fsrs |

## Dataset files

| File | Who may read it | Content |
|---|---|---|
| `reviews.csv` | optimizer | one row per session; first 7 columns are the review dataset schema, then `line_id, review_id, day, timestamp, n_moves, n_correct, baseline_ms` |
| `moves.csv` | grader / latency work | per move: `review_id, ply, correct, time_ms` |
| `openings.csv` | anyone | lines used: `line_id, opening_name, pgn, color, n_moves, plies` |
| `split.csv` | anyone | `agent_name` → train / val, split by player |
| `hidden/agents.csv` | evaluation only | archetype, true w0..w20, traits |
| `hidden/truth.csv` | evaluation only | per review: true R, recalled, reps, S/D before and after, app's R |

Never train on `hidden/`.

## Using the evaluation helpers

```python
from tempo_sim.evaluate import replay, metrics, param_recovery, to_fsrs_review_logs
logs = to_fsrs_review_logs(train_reviews)          # -> fsrs.Optimizer(logs)
p = replay(val_reviews, lambda agent: fitted_w)    # predicted R per review
metrics((val_reviews.grade > 1), p)                # log_loss, rmse_bins, auc
param_recovery(fitted_df, hidden_agents_df)        # per-weight relative error
```

`to_fsrs_review_logs` stamps reviews at midnight on purpose: py-fsrs computes
elapsed time with `timedelta.days`, so clock times (22:00 → 07:00 next day)
would turn 1-day gaps into same-day reviews. The real app should log
calendar-day differences in the player's local time.
