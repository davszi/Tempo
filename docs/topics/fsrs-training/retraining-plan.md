# Retraining FSRS-6 on the cleaned opening catalog

## Scope and status

This plan belongs to the [FSRS training](fsrs-training.md) topic. It covers
retraining both training variants on the cleaned opening catalog, two new
experiment arms that train against the true recall, a new accuracy metric in
days, and removing datasets from the variant folders.

Status: planned on 2026-11-13, not started. Nothing below has been run except
the [motivation probe](#motivation-probe-2026-11-13).

Terms used here:

- **Opening catalog**: the tables `opening_lines` and `opening_families` in
  `backend/tempo_demo.sqlite`.
- **Variant**: one of the two training code bases,
  `ml/ml_1000bots/` (1,000 synthetic agents) and `ml/ml_300bots/` (300
  synthetic clients).
- **Arm**: one training run of one variant with one target.
- **True recall**: the hidden chance of passing that the simulator rolls the
  dice with. It exists only for synthetic players.

## Why retrain

- Commit `5cbe0a6` removed every line with fewer than four White moves from
  the opening catalog. It went from 3,865 lines in 140 families to 2,719 lines
  in 91 families (see the [opening library](../opening-library/opening-library.md)).
- Both trained models were built on the old catalog:
  - `ml_1000bots`: dataset `tempo_v1`, 300 lines drawn from the old
    `openings/lichess_openings_classified.csv`. It contained no short lines,
    but the simulator draws lines by catalog row, so a new catalog gives a
    different line set.
  - `ml_300bots`: dataset `fsrs-synthetic-v1`, built from
    `ml/ml_300bots/openings/opening_lines.csv` (sha256 `a8ffd012…` in its
    `manifest.json`). That file is not in the repository, so the 300-client
    generator cannot run as it stands.
- The current scores (log-loss, Brier, RMSE(bins), AUC) do not say what an
  error means for a player. A metric in days does.

## Decisions

Decided in the 2026-11-13 discussion:

1. Keep training on the binary target (pass = grade > 1) in both variants,
   and retrain both on the cleaned opening catalog.
2. Add one experiment arm per variant that trains against the true recall
   instead of pass/fail, with the mean squared error (MSE) between the
   predicted and the true recall as the loss. It uses the same agent
   configuration and the same generated data as the binary arm of its
   variant; only the target and the loss change.
3. Every arm reports the error in days: predicted against true stability
   (see [days metric](#days-metric)).
4. The variant folders hold no datasets. Both variants read the opening
   catalog from `backend/tempo_demo.sqlite`. Generated training data is not
   committed.

The true-recall arms are a diagnostic, not a candidate for the app: real
players have no true recall. They are the one deliberate exception to "Never
train on `hidden/`" in `ml/ml_1000bots/README.md`, and their weights must
never be copied to `backend/fitted_global.csv`.

Proposed in this plan and not yet accepted: the metric details (90% target,
medians, bands), the control arm A1c, folder names, the shared line key and
the order of work.

## The arms

| Arm | Variant | Players | Target | Loss | Optimizer |
|---|---|---|---|---|---|
| A1 | `ml_1000bots` | 1,000 agents: 800 train, 200 val; plus 200 control agents | pass (grade > 1) | log-loss | py-fsrs 6.3.2 `Optimizer`, as in the first run |
| A2 | `ml_300bots` | 300 clients: 210 fit, 30 validation, 60 test; plus 60 hold-out clients | clean session (grade > 1) | log-loss | L-BFGS-B, `tempo_ml/fsrs/train.py` |
| B1 | `ml_1000bots` | same agents and data as A1 | true recall `R_true` (`hidden/truth.csv`) | MSE | the shared trainer (see [task 4](#task-4-shared-trainer-and-the-b1-b2-and-a1c-arms)) |
| B2 | `ml_300bots` | same clients and data as A2 | true chance of a clean session `p_clean` (`ground_truth.csv`) | MSE | `train.py` with the target and loss switched ([task 4](#task-4-shared-trainer-and-the-b1-b2-and-a1c-arms)) |
| A1c (proposed) | `ml_1000bots` | same as A1 | pass (grade > 1) | log-loss | the shared trainer, same as B1 |

Each arm returns one global set of 21 FSRS-6 weights.

- **Why `p_clean` for B2:** the 300-client binary target is "every move
  right". Its true chance is `p_clean = R_move ** M`, not the per-move
  `retrievability`.
- **Why A1c:** py-fsrs `Optimizer` only accepts review ratings, so B1 needs
  its own trainer. A1 and B1 would then differ in target, loss *and*
  optimizer. A1c runs the binary target through the B1 trainer, so A1c
  against B1 changes only target and loss. A2 and B2 already share an
  optimizer.
- Per-player fine-tuning (`personal*.py`, the personalisation step of
  `train.py`) is not part of the arms. Its earlier results stay historical.

## Metrics

All arms are scored on the same evaluation players, which no arm trains on or
uses to choose settings:

- `ml_1000bots`: the 200 val agents and the 200 control agents.
- `ml_300bots`: the 60 test clients and the 60 hold-out clients.

| Metric | Unit | Reported now | Change |
|---|---|---|---|
| log-loss | nats per review | both variants | none |
| Brier score | probability² | `ml_300bots` | add to `ml_1000bots` |
| RMSE(bins) | percentage points | `ml_1000bots` | add to `ml_300bots` |
| AUC | 0.5–1 | both | none |
| error against true recall: RMSE and MAE | percentage points | MAE only, `ml_300bots` | both metrics in both variants |
| [days metric](#days-metric) | days and % | none | new, both variants |

Baselines: default FSRS-6 weights in both variants; a constant equal to the
training players' pass rate in `ml_300bots`; true weights (oracle) in
`ml_1000bots` only, because the 300-client hidden memory is not FSRS.

### Days metric

After every session of an evaluation player (learning or review), each model
updates its state for the line. Then:

- **Predicted days** `d_pred`: days until the model's predicted chance drops
  to 90%. For FSRS-6 this equals the predicted stability `S_pred`, because
  FSRS-6 defines `R(S) = 0.9`.
- **True days** `d_true`: days until the hidden true chance drops to 90%.
  - `ml_1000bots`: the hidden memory is FSRS-6, so `d_true = S_true`
    (`S_after` in `hidden/truth.csv`).
  - `ml_300bots`: a clean session needs all `M` moves, so the true chance is
    `R(t)^M` with `R(t) = (1 + F t / S)^(-C)` and `F = 0.9^(-1/C) - 1`.
    Solving `R(t)^M = 0.9` gives
    `d_true = S / F * ((0.9^(1/M))^(-1/C) - 1)`, with `S = stability_after`
    from `ground_truth.csv` and `C` from `clients.csv`. For `M = 1` this
    reduces to `d_true = S`.
- **Error** = `d_pred - d_true`, in days. Negative means the model thinks the
  player forgets sooner than they really do, so the review comes too early.
  Positive means it comes too late.

Report per arm and baseline:

- median error, median absolute error, median relative error
  (`error / d_true`, in %), share of sessions scheduled too early;
- the same split by `d_true` band (under 7, 7–30, 30 or more days) and by
  session type (after learning, after a review);
- the mean error, marked as dominated by long intervals;
- the number of sessions with `d_true` beyond the 180-day simulated horizon,
  which the data cannot check.

Why 90%: at 90% the days error is exactly the stability difference the team
asked for, and 90% is the app's default desired retention. Why medians: in
the probe, single true intervals reached 1,867 days and decided the mean.

Proposed homes: a function in `ml/ml_1000bots/tempo_sim/evaluate.py` used by
`fit_global.py`, and an extension of `metrics()` in
`ml/ml_300bots/ml_engine/src/tempo_ml/fsrs/train.py` used by `benchmark.py`.
Unit tests: `M = 1` gives `d_true = S`, and a model scored against its own
weights gives zero error.

## Opening catalog and datasets

### Read the catalog from the backend

`backend/tempo_demo.sqlite` (read-only) holds 2,719 lines. Since commit
`0d2dc08` the catalog is two tables: `opening_lines`
(`line_id, family_id, name, eco, moves_uci, side_in_games`) and
`opening_families` (`family_id, name, family_side`). The loaders join them
to get each line's family and family side.

| Variant | Current loader | Columns it needs | Change |
|---|---|---|---|
| `ml_1000bots` | `tempo_sim/play.py`, `_library_catalogue`, reads `openings/lichess_openings_classified.csv` (`config.py`, `openings_file`) | name, pgn (to count plies), family_side | read SQLite; plies = number of UCI moves |
| `ml_300bots` | `tempo_ml/openings.py`, `load_opening_lines`, reads the missing `ml/ml_300bots/openings/opening_lines.csv` | eco, family, name, pgn, plies, white_moves, black_moves, family_side, side_in_games, n_games | read SQLite; derive plies and move counts from `moves_uci`; `n_games` is missing (see [open questions](#open-questions)) |

Proposed: both variants use the backend `line_id` as the line key, so lines
match across variants and the app.

### Remove datasets from the variant folders

| Path | Content | Size | After removal |
|---|---|---|---|
| `ml/ml_1000bots/data/tempo_v1/` | input of the first `ml_1000bots` run | about 40 MB | Retrievable at commit `5cbe0a6`. Hashes stay in `runs/2026-11-11-first-training/dataset_MANIFEST.txt`. Drop the `!data/tempo_v1/` exception from `ml/ml_1000bots/.gitignore`. |
| `ml/ml_300bots/ml_engine/experiments/fsrs-synthetic-v1/data/*.csv` | input of the `ml_300bots` run | about 35 MB | Keep `manifest.json` (hashes). Add an ignore rule; that experiment's README already says these CSVs are meant to be git-ignored. |
| `ml/ml_300bots/ml_engine/experiments/fsrs-synthetic-v1/holdout_data/*.csv` | its hold-out clients | about 7 MB | same |
| `ml/ml_1000bots/openings/` data files: `lichess_openings.tsv`, `lichess_openings_classified.csv`, `family_side_evidence.csv` | the catalog's Lichess source and build outputs | about 1.2 MB | Not removed until the [open question](#open-questions) on where the catalog build lives is decided. |

Kept: the run records and their outputs,
`ml/ml_1000bots/runs/2026-11-11-first-training/` and
`fsrs-synthetic-v1/results/`. They become historical results on the old
catalog. New generated data stays local and git-ignored. Each new run folder
records its generation command, seed and file hashes.

## Order of work

Summary; the [implementation guide](#implementation-guide-for-agents) has
the files, commands and checks for each step.

1. **Clean up.** Remove the datasets listed above and update the ignore rules,
   the README files and [FSRS training](fsrs-training.md) where they point at
   committed data.
2. **Catalog loaders.** Both variants read the backend opening catalog. The
   existing tests pass: 21 in `ml_1000bots`, 34 in `ml_300bots`.
3. **Metrics.** Add the error against true recall and the days metric to both
   evaluation paths, with the unit tests above.
4. **True-recall trainers.** Add the MSE objective (B2), the B1 trainer and
   A1c.
5. **Generate data**, uncommitted:
   - `ml_1000bots`: the `tempo_v1` settings with the new catalog, seed 7, plus
     a control set with seed 2000;
   - `ml_300bots`: seed 20261111, plus hold-out clients with seed 20261112.
6. **Train and evaluate** A1, A2, B1, B2 and A1c on the evaluation players
   above.
7. **Record.** New run folders, proposed
   `ml/ml_1000bots/runs/<date>-cleaned-catalog/` and
   `ml/ml_300bots/ml_engine/experiments/fsrs-synthetic-v2/`, each with a
   summary, reproduction commands, environment and raw outputs. Update the
   results in [FSRS training](fsrs-training.md) and add a worklog entry.

## Implementation guide for agents

Each task below names its files, what to build, and when it is done. Do them
in order; each task's checks must pass before the next starts. Paths are
relative to the repository root. Before changing code, read
`.docs-kit/rules/engineering/code.md`; before running the experiments, read
`.docs-kit/rules/experiments/workflow.md`.

Rules for every task:

- Never use `hidden/truth.csv`, `hidden/agents.csv` or `ground_truth.csv`
  in A runs. B runs may read them for **training players only**.
- Evaluation players (1000: val and control; 300: test and hold-out) are
  never used for training or for picking settings.
- Do not change `backend/tempo_demo.sqlite`; open it read-only
  (`sqlite3.connect(Path(p).resolve().as_uri() + "?mode=ro", uri=True)`).
- Do not commit generated data. Commit code, tests, run records and small
  result files.

### Task 1: remove the datasets

- Delete the paths in [remove datasets](#remove-datasets-from-the-variant-folders),
  except the `openings/` files (open question).
- `ml/ml_1000bots/.gitignore`: remove the `!data/tempo_v1/` line.
- Add an ignore rule for `ml/ml_300bots/ml_engine/experiments/*/data/*.csv`
  and `.../holdout_data/*.csv`; keep the `manifest.json` files.
- Update every text that says the data is in Git: `ml/ml_1000bots/README.md`,
  `README.md` (line about `ml/data/tempo_v1/`),
  [FSRS training](fsrs-training.md) "Dataset tempo_v1", and
  `runs/2026-11-11-first-training/SUMMARY.md` "Inputs" (say the data is at
  commit `5cbe0a6`, hashes in `dataset_MANIFEST.txt`).
- Done when: `git ls-files ml | grep -E 'data/.*\.csv$'` prints nothing, and
  no README or record says a deleted file is in the repository.

### Task 2: read the catalog from the backend

Write one small reader per variant (no shared module between the variants):

```sql
SELECT l.line_id, l.name, l.eco, l.moves_uci, l.side_in_games,
       f.name AS family, f.family_side
FROM opening_lines AS l JOIN opening_families AS f USING (family_id)
ORDER BY l.line_id
```

Derived values: `plies = len(moves_uci.split())`,
`white_moves = (plies + 1) // 2`, `black_moves = plies // 2`.

- `ml_1000bots`: in `tempo_sim/config.py` replace `openings_file` by
  `catalog_db = "../../backend/tempo_demo.sqlite"` (relative to
  `ml/ml_1000bots/`). In `tempo_sim/play.py`, `_library_catalogue` reads the
  query above instead of the CSV; the moves the player must produce are
  counted from `plies` and the side from `family_side` as today. Line IDs
  become `f"line_{line_id}"` with the backend `line_id`.
- `ml_300bots`: in `tempo_ml/openings.py` replace `DEFAULT_LINES_CSV` by the
  database path (`Path(__file__).resolve().parents[5] / "backend" / "tempo_demo.sqlite"`;
  `parents[5]` of `ml/ml_300bots/ml_engine/src/tempo_ml/openings.py` is the
  repository root) and let `load_opening_lines` read the query. `line_id` becomes
  the backend `line_id` as a string. `family_games` has no source: set it to
  0 (uniform family choice) until the [open question](#open-questions) is
  decided, and say so in the run record.
- Update the tests that build lines from a CSV
  (`ml/ml_300bots/ml_engine/tests/`) to use a tiny temporary SQLite file
  with the two tables.
- Done when: both test suites pass (`python -m pytest tests/` in
  `ml/ml_1000bots/`: 21 tests; `python -m pytest` in
  `ml/ml_300bots/ml_engine/`: 34 tests, plus any new ones), and a small
  generation run (`generate.py` with a config setting `"n_agents": 10`;
  `generate --clients-per-archetype 2`)
  only uses lines that exist in the backend catalog.

### Task 3: metrics

Add to both variants, with the same names and units:

| Name in output | Formula | Unit |
|---|---|---|
| `rmse_vs_truth` | `sqrt(mean((p - p_true)^2))` | probability (report × 100 as percentage points) |
| `mae_vs_truth` | `mean(abs(p - p_true))` | probability |
| `brier` | `mean((p - y)^2)` | probability² |
| `rmse_bins` | as `tempo_sim/evaluate.py` `metrics()`, 20 bins | probability |
| `days_*` | see [days metric](#days-metric) | days, % |

`p_true` is `R_true` (1000) or `p_clean` (300) for the same review.

Days metric, step by step:

1. Add a function that returns the model's stability **after** every
   session: in `ml_300bots`, `fsrs/model.py` gets
   `predict_states(w, t, g, valid) -> (r, s_after)`, a copy of `predict`
   that also stores `s` after each step (including step 0). `predict` stays
   unchanged.
2. `d_pred = s_after` (FSRS-6 reaches 90% exactly at `t = S`).
3. `d_true`:
   - 1000: `S_after` from `hidden/truth.csv`, joined by `review_id`.
   - 300: `S = stability_after`, `M = num_moves` (both `ground_truth.csv`,
     same row as `sessions.csv`), `C` from `clients.csv` by `agent_name`;
     `F = 0.9**(-1/C) - 1`; `d_true = S / F * ((0.9**(1/M))**(-1/C) - 1)`.
4. Use every session of an evaluation player, learning sessions included;
   drop sessions where `d_true` is missing.
5. Output keys: `days_median_error`, `days_median_abs_error`,
   `days_median_rel_error`, `days_share_too_early`, `days_mean_error`,
   `days_n_beyond_horizon` (`d_true > 180`), and the same first three per
   band `lt7`, `7to30`, `ge30` and per session type `after_learning`,
   `after_review`.

Put the 1000 version in `tempo_sim/evaluate.py` (new function
`days_error(reviews, truth, weights_for)`) and print it from `fit_global.py`;
put the 300 version in `tempo_ml/fsrs/train.py` `metrics()` (new optional
arguments) so that `train.py` and `benchmark.py` both report it.

Tests (new):

- `d_true` with `M = 1` equals `S`.
- Scoring a model against data generated from its own weights gives
  `days_median_abs_error == 0` (1000: run `replay` with the true weights).
- `rmse_vs_truth` is 0 when `p == p_true`.

Done when: the tests pass and `fit_global.py` on a 50-agent dataset prints
all keys above.

### Task 4: shared trainer and the B1, B2 and A1c arms

One trainer serves B1, B2 and A1c: the vectorised FSRS-6 model and bounded
L-BFGS-B fit that already exist in `ml_300bots`
(`tempo_ml/fsrs/model.py` `predict`, bounds `LOWER_BOUNDS`/`UPPER_BOUNDS`;
`tempo_ml/fsrs/train.py` `fit`). Do not replay `tempo_sim/fsrs6.py` review
by review: with finite-difference gradients that is 22 full replays per
optimizer step and takes hours.

**Generalise the objective** in `train.py`:

```python
def objective(w, cards, mask, target, loss="bce", prior=None, lam=0.0):
    p = predict(w, cards.t, cards.g, cards.valid)
    if loss == "bce":
        value = bce(p[mask], target[mask]).mean()
    elif loss == "mse":
        value = np.mean((p[mask] - target[mask]) ** 2)
    ...  # prior term unchanged
```

`fit()` passes `target` and `loss` through. Default `target=cards.y`,
`loss="bce"`, so A2 runs exactly as before. Add
`--target {pass,true}` to `train.py`. `pass` uses `cards.y` with
`bce`; `true` uses `p_clean` aligned with `cards.row` (as `truth_all` is
today) with `mse`. That is B2.

**1000-agent loader** for the shared trainer, new file
`ml/ml_1000bots/tempo_sim/cards.py`:

- `load_cards_1000(data_dir, agents) -> Cards` builds the same arrays as
  `tempo_ml/fsrs/data.py` `load_cards`, from `reviews.csv`.
- Key a card by `(agent_name, line_id)`, **not** by opening name: 688 names
  repeat in the catalog.
- Sort by `agent_name, line_id, day, review_id`. `t` = `t_days`, `g` =
  `grade`. Loss mask = review status `review` or `relearning` and `t >= 1`.
- Also return `review_id` per cell (`-1` where empty), to join `R_true` from
  `hidden/truth.csv`.

**1000-agent fit script**, new file `ml/ml_1000bots/fit_shared.py`:

```
python fit_shared.py <data_dir> <out_dir> --target {pass,true}
```

- Imports `tempo_ml.fsrs.model` and `tempo_ml.fsrs.train.fit`. Install the
  300 package once with `pip install -e ../ml_300bots/ml_engine[train]` and
  add `scipy` to `ml/ml_1000bots/requirements.txt`.
- Trains on the train agents of `split.csv` only. `--target pass` is A1c
  (`y = grade > 1`, `bce`); `--target true` is B1 (`R_true`, `mse`).
- Start from the default FSRS-6 weights, L-BFGS-B within the FSRS bounds,
  `maxiter=300`, `eps=1e-6` (the settings of `train.py`).
- Writes `fitted_<target>.csv` (columns `w0..w20`, like `fitted_global.csv`)
  and `fit_<target>.txt` with the optimizer result and the metrics of task 3
  on val agents, computed with `tempo_sim.evaluate.replay` so the numbers
  are comparable with A1.

Checks before the real runs:

- **Recovery test.** Generate `configs/recovery_test.json` (300 agents, one
  shared weight vector) and fit it with `--target true`. Proposed bar (not
  yet agreed): the identifiable weights (all except w0, w1, w3, w19; see
  `fit_global.py`) come back within 10% of `hidden/agents.csv`, and
  `rmse_vs_truth` on val is below 0.005. If not, the trainer or the
  alignment of `R_true` is wrong; stop and report.
- **Same model.** On 100 random cards, `tempo_ml.fsrs.model.predict` and
  `tempo_sim.evaluate.replay` give the same predictions to 1e-9 for the same
  weights.
- **Unit test.** With `target == predict(w)` the `mse` objective is 0 at `w`.

Expected run time: about 5 minutes per fit on a laptop (the 300-client
general fit took 279 s on 62,053 reviews).

### Task 5: generate data

- 1000: new config `ml/ml_1000bots/configs/tempo_v2.json` = `tempo_v1.json`
  plus the backend catalog. Run
  `python generate.py --out data/tempo_v2 --config configs/tempo_v2.json`,
  and the control set as `experiments/shift_benchmark.py --control` does
  (seed 2000).
- 300: `python -m tempo_ml.synthetic_data.generate --out experiments/fsrs-synthetic-v2/data --seed 20261111`
  and `--out experiments/fsrs-synthetic-v2/holdout_data --seed 20261112 --clients-per-archetype 20`.
- Copy each `MANIFEST.txt` / `manifest.json` into the run folder.
- Done when: the data folders are git-ignored and the run folders hold the
  manifests.

### Task 6: train and evaluate

| Arm | Command (from the variant folder) |
|---|---|
| A1 | `python fit_global.py data/tempo_v2 runs/<date>-cleaned-catalog/binary` |
| A1c | `python fit_shared.py data/tempo_v2 runs/<date>-cleaned-catalog/shared --target pass` |
| B1 | `python fit_shared.py data/tempo_v2 runs/<date>-cleaned-catalog/shared --target true` |
| A2 | `python -m tempo_ml.fsrs.train --data experiments/fsrs-synthetic-v2/data --out experiments/fsrs-synthetic-v2/results-binary --seed 7 --target pass --no-personalise` |
| B2 | same with `--out .../results-true-recall --target true` |

Then score every arm and the baselines on the second evaluation set: the
1000 control agents with `experiments/shift_benchmark.py --control`, the 300
hold-out clients with `python -m tempo_ml.fsrs.benchmark`. Both must report
the task 3 metrics. `train.py` always runs its personalisation step; add a
`--no-personalise` flag and use it for A2 and B2, since per-player tuning is
not part of these arms.

### Task 7: record

- One `SUMMARY.md` per run folder: question, kind, baseline, commands,
  environment (Python and package versions, OS, CPU), source commit, data
  hashes, a results table per evaluation set with every task 3 metric for
  every arm and baseline, attempts and failures, caveats.
- Update [FSRS training](fsrs-training.md) "Training and results" with the
  new numbers. Keep the old tables, labelled as historical results on the
  old catalog.
- Add a worklog entry. Delete this plan's line in `docs/open/OPEN.md` when
  every task is done.
- Do not change `backend/fitted_global.csv` until the team answers the
  first [open question](#open-questions).

## Experiment protocol

- **Questions.**
  1. Do the retrained binary weights still beat the defaults on the cleaned
     catalog? By how much, in percentage points of recall and in days?
  2. How much closer do the weights get when trained on the true recall
     instead of pass/fail? This bounds what better labels could give; the
     remaining gap to the oracle comes from one shared weight set.
- **Kind.** Exploratory investigation. No pass/fail bar is fixed.
- **Decisions it informs.**
  - Which binary arm's weights replace the synthetic weights in
    `backend/fitted_global.csv`.
  - Whether richer training signals are worth building. An example is
    hesitation time relative to the player's own speed. If B arms barely
    beat A arms, pass/fail labels are not the bottleneck.
- **Baselines.** Default FSRS-6 weights (what ships without training);
  constant pass rate (`ml_300bots`); oracle true weights (`ml_1000bots`).
- **Separation.** B arms read hidden truth for training players only.
  Evaluation players are never used for training or for choosing settings.
- **Budget and stopping.** About one hour of laptop CPU for all arms (the
  first runs took about 100 s per `ml_1000bots` global fit and 997 s for
  `ml_300bots` training). Stop when the five arms are evaluated. A setting
  changed after seeing evaluation results is a new, recorded attempt.
- **Caveats.**
  - Synthetic players only.
  - The `ml_1000bots` hidden memory is FSRS-6 itself, so its results are
    optimistic.
  - The `ml_300bots` hidden memory is not FSRS, so it has no oracle.

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
  values in [FSRS training](fsrs-training.md#training-and-results) exactly.
- This probe measured days to each player's own target retention (80–95%),
  not the 90% proposed above, so its days numbers are motivation, not
  baselines for this plan.
- Source: commit `e130687`. The inputs are unchanged in `5cbe0a6`.
- Environment: Python 3.12.12, numpy 2.3.5, Windows 11.
- Scripts: [`evidence/2026-11-13-probe/`](evidence/2026-11-13-probe/). Run
  them from the repository root:
  - `python -I docs/topics/fsrs-training/evidence/2026-11-13-probe/accuracy_check.py ml/ml_1000bots`
  - `python -I docs/topics/fsrs-training/evidence/2026-11-13-probe/days_error.py ml/ml_1000bots`

## Open questions

- Which binary arm's weights go to `backend/fitted_global.csv`, A1 or A2?
- Where does the catalog build live once the variant folders hold no data?
  The build is the Lichess TSV, `classify.py`, `side_evidence.py` and the
  evidence CSV, owned by the [opening library](../opening-library/opening-library.md).
  Options: move it to a shared folder, or keep only the SQLite catalog and
  recover the source from Git history.
- `ml_300bots` weights its repertoire choice by family popularity (`n_games`,
  `synthetic_data/generate.py` line 105). The SQLite catalog has no `n_games`.
  Options: add it to the catalog, or choose families uniformly.
- Should `agent_curve.py` and the per-player experiments be rerun on the new
  data? They are not part of this plan.
