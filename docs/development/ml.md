# ML setup and reproducibility

TEMPO machine-learning code: synthetic clients, dataset generation, FSRS-6
training and evaluation. Method, results and decisions:
[FSRS training](../topics/fsrs-training/fsrs-training.md).

Use Python 3.12 or later in an isolated environment. The `train` extra installs
SciPy and pandas; the `test` extra also installs pytest and py-fsrs 6.3.2.
Py-fsrs is used for reference checks and the retained A1 optimizer experiment,
not by the package's L-BFGS-B trainer.

```bash
cd ml
python -m pip install -e ".[train,test]"
python -m pytest

# generate a synthetic dataset (reads backend/tempo_demo.sqlite), then fit FSRS-6 on it
python -m tempo_ml.simulator.generate --config configs/multiplicative-memory.json --out data/<name>   # or configs/fsrs-memory.json
python -m tempo_ml.fsrs.train --data data/<name> --out experiments/<date>-<name>/results/binary --seed 7 --target pass --no-personalise
```

- `tempo_ml/catalog.py`: reads the opening catalog from `backend/tempo_demo.sqlite`.
- `tempo_ml/fsrs/`: the vectorised FSRS-6 model and input layout (`model.py`) and the L-BFGS-B trainer (`train.py`, target pass/fail or true recall).
- `tempo_ml/simulator/`: virtual players. `clients.py` archetypes, per-player spread and the client; `memory/multiplicative.py` (default) and `memory/fsrs.py` (`"memory": "fsrs"`) their hidden memory; `recall.py` per-move recall, retries and move times; `practice.py` repertoire, new lines and scheduling; `grading.py` Again/Hard/Good/Easy and the session record; `generate.py` writes a dataset.
- `tempo_ml/evaluate/`: `metrics.py` (log-loss, Brier, calibration, AUC, error against the true chance) and `days.py` (error in days to 90%).
- `configs/`: generator settings for multiplicative or FSRS hidden memory. The published November 13 and 14 runs used different catalog groupings (91 and 82 families). Running a configuration against today's SQLite file is not, by itself, an exact historical reproduction; use each experiment's source pin, input identity and instructions.
- `experiments/<date>-<name>/`: one folder per run; `SUMMARY.md` is its record, scripts that belong only to it sit beside it.
- `tests/`: `test_simulator.py`, `test_memory_models.py`, `test_trainers.py`, `test_metrics.py`.
- `data/`: generated datasets, ignored by Git; each experiment's `dataset_MANIFEST.txt` says how to rebuild them.

## CLI contracts

Run from `ml/` after installation. `pyproject.toml` requires Python >=3.12
and NumPy >=1.26; `train` adds SciPy >=1.11 and pandas >=2.1; `test` adds
pytest >=8 and fsrs==6.3.2. There is no packaged console-script entrypoint;
invoke modules with `python -m`.

| Module | Required and optional arguments |
|---|---|
| `tempo_ml.simulator.generate` | Required `--out`; optional `--config`, `--seed`, `--clients-per-archetype`, `--horizon-days`, `--catalog` |
| `tempo_ml.fsrs.train` | Required `--data`, `--out`; optional `--seed` (7), `--target pass` or `true`, `--no-personalise` |

Generator JSON must contain `GenerationConfig` fields; unknown keys are
rejected and lists become tuples. CLI seed, client count and horizon override
JSON. The default catalog path resolves from the source tree to
`backend/tempo_demo.sqlite`; source location matters. `--catalog` selects
another read-only SQLite catalog. Population, scheduling and memory settings
belong to [Synthetic Players](../topics/synthetic-clients/record.md#9-practice-policy-generation-and-demo-producer).

The trainer currently requires `sessions.csv`, `ground_truth.csv`,
`clients.csv` and `manifest.json` even for the binary target. It is a
synthetic-experiment CLI, not a completed human-data fitting flow. Artifacts
and optimizer limits belong to [FSRS Training](../topics/fsrs-training/fsrs-training.md#artifacts-and-reproduction).
The `true` target is diagnostic; its weights must never replace the app's
`backend/fitted_global.csv`.

The independent demo producer runs from the repository root using the
backend environment in [project context](../PROJECT_CONTEXT.md#python-backend):

```powershell
python -m backend.synthetic_clients --output <demo-sessions.csv> --clients-per-profile 1 --sessions 12 --seed 42
```

Optional `--database <catalog.sqlite>` reads catalog lines;
`--one-line-per-family` requires that database. Counts must be positive,
input lines nonempty, output distinct from the database, and the output's
parent directory already present. Defaults use two built-in demo lines.
This CLI uses default FSRS scheduling without the runtime fitted weights
and exports no truth sidecars. [Synthetic Players](../topics/synthetic-clients/record.md#backend-demo-producer)
and [Review Dataset](../topics/review-dataset/record.md#5-generated-files-and-producer-boundaries)
explain its meaning and limits.

## Verification scope

The 2026-11-15 audit inspected metadata, both CLI parsers, every package
module, four configs and four ML test files at
`788e06039dd2869b23261dd80ea8fc49367ab33c`. It did not install dependencies,
execute these commands, generate data or rerun training/tests. Dated runs
retain their executed checks. The suite includes fitting and generator
tests; running it performs compute/data generation even though outputs go
to pytest temporary directories.


## Fresh dataset output directories

Use a fresh output directory for each independently identified generation,
especially when switching hidden-memory models. The generator overwrites its
normal files but does not clean unrelated or stale CSVs: an old
`memory_weights.csv` can remain after multiplicative generation, and all CSVs
present are hashed into the new manifest. This source-derived limitation is
explained in [Review Dataset](../topics/review-dataset/record.md#5-generated-files-and-producer-boundaries).
Preserve existing datasets and results; select a new output path instead of
removing saved data to satisfy this precondition. No historical contamination
is established by the source audit.
