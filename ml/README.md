# ML setup and reproducibility

TEMPO machine-learning code: synthetic clients, dataset generation, FSRS-6
training and evaluation. Method, results and decisions:
[FSRS training](../docs/topics/fsrs-training/fsrs-training.md).

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
