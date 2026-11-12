# Training results on data/tempo_v1 (2026-11-11)

Dataset: 1000 synthetic clients (team spec, 3 archetypes), 180 days, 97,605
reviews; 800 train / 200 val agents. Score: predicting pass (grade > 1) on
val agents; log-loss, lower is better.

Val agents (200, from tempo_v1):

| | val log-loss | RMSE(bins) | AUC |
|---|---|---|---|
| default FSRS-6 | 0.3930 | 0.0335 | 0.670 |
| global fit | 0.3910 | 0.0201 | 0.670 |
| true weights (oracle) | 0.3849 | 0.0126 | 0.692 |

Control set (200 new agents, same rules, seed 2000, 20,370 reviews):

| | log-loss | RMSE(bins) | AUC |
|---|---|---|---|
| default FSRS-6 | 0.3964 | 0.0457 | 0.687 |
| global fit | 0.3917 | 0.0157 | 0.688 |
| true weights (oracle) | 0.3866 | 0.0144 | 0.704 |

1. **One global fit beats the defaults**, closing ~25% of the gap to the
   oracle (95% bootstrap interval 11%-37%, `analysis.txt`), and recovers the
   decay C (true median 0.49, fitted 0.43, default 0.15).
   **Control test on new players** (`control/shift_benchmark.md`, control
   scenario): 200 fresh agents generated with the same rules as tempo_v1 but
   a new seed, every review scored. The global fit beats the defaults again
   (gain 0.0047, 95% interval 0.0023-0.0073) and here closes 48% of the gap.
   25% on the val agents and 48% here are both samples of 200 players, so
   read it as "about a quarter to a half".
2. **Few players are enough for the global fit** (`agent_curve.csv/png`):
   ~100 agents (~10k reviews) reach the plateau (0.3911); 25 agents already
   beat the defaults on average (0.3924, range 0.3910-0.3932 over 3 draws).
3. **Per-player fits do not help with 4 months of data**
   (`personal.txt`, `personal_light.txt`; train on a player's first 70% of
   days, score the last 30%):
   - py-fsrs returns the default weights below 512 reviews; players have ~56.
   - Fitting only C per player: without a prior the chosen C is badly biased
     (0.17-0.29 vs true 0.35-0.66) and the score gets worse (0.3963 vs
     global 0.3946); with a prior it stays at the global value.
   - Most of the remaining gap to the oracle is per-player variation that
     ~56 reviews cannot reveal.

## Question and kind

Exploratory investigation. Question: does training FSRS-6 weights on
synthetic clients beat the default weights, how many clients does it need,
and does a per-player fit add anything? It informs how the ML engine starts
(one global fit vs per-player fits) and how much real data to collect before
retraining. Baseline: default FSRS-6 weights (what ships without training).
Upper bound: each agent's true weights. Budget: one working session on a
laptop; stop when the three questions are answered. No pass/fail bar was
fixed in advance.

Every parameter of the dataset and the optimizer is listed in
`TRAINING_PARAMETERS.md`. Method and topic-level conclusions:
`docs/topics/fsrs-training/fsrs-training.md`.

## Inputs, code and environment

- Dataset: `ml/data/tempo_v1/` (in Git). File and code hashes:
  `dataset_MANIFEST.txt` (a copy of the dataset's `MANIFEST.txt`). Regenerating with
  `python generate.py --out data/tempo_v1 --config configs/tempo_v1.json`
  reproduced all seven data files byte for byte (2026-11-12).
- Source pin: the runs used the uncommitted working tree. The commit that
  lands this directory contains that code. The simulator files match the
  sha256 in `dataset_MANIFEST.txt`. Since the runs, `experiments/agent_curve.py`
  gained a `--plot` mode (the figure was redrawn from the saved CSV with it),
  `experiments/personal.py` gained a docstring note, and
  `experiments/shift_benchmark.py` gained `--control` (the control output
  was regenerated with it and is identical to the first run).
- Environment: Python 3.13.3, numpy 2.5.4, pandas 3.1.1, fsrs 6.3.2,
  torch 2.15.0 (CPU), macOS 15.5, Apple M4, 16 GB. Versions are pinned in
  `ml/requirements.txt`.
- Run times: global fit about 100 s; agent curve about 6 min; per-player
  scripts a few minutes each.

## Attempts and failures

- `personal.py`: every "personal" fit silently returned the default weights,
  because py-fsrs needs at least 512 reviews per fit (`mini_batch_size`).
  Its numbers are kept as that negative result. `personal_light.py` was added
  to test a fit that works on little data.
- `analyze_global.py` also scored one fit per archetype (0.3905 on val,
  0.3921 on the control set), no better than the global fit.
- While refactoring the plot code, `agent_curve.py` briefly contained a
  duplicated block. It was removed before the figure was redrawn; the CSV
  results were produced before the edit.

## Limits

- The hidden memory is FSRS-6, so the model is correct by construction and
  the results are optimistic.
- One dataset seed (7) and one control seed (2000). Bootstrap intervals cover
  the choice of players, not the choice of simulator settings.
- The fitted weights are synthetic and must not ship as real-player weights.

## Reproduce

Run in `ml/`; `data/tempo_v1` is in Git (or regenerate it with `generate.py`):

    python fit_global.py data/tempo_v1 runs/2026-11-11-first-training
    python experiments/agent_curve.py data/tempo_v1 runs/2026-11-11-first-training
    python experiments/personal.py data/tempo_v1 runs/2026-11-11-first-training
    python experiments/personal_light.py data/tempo_v1 runs/2026-11-11-first-training
    python experiments/analyze_global.py data/tempo_v1 runs/2026-11-11-first-training
    python experiments/shift_benchmark.py data/tempo_v1 runs/2026-11-11-first-training/fitted_global.csv runs/2026-11-11-first-training/control --control
