# ml

TEMPO machine-learning code: synthetic clients, dataset generation, FSRS-6
training and evaluation. Method, results and decisions:
[FSRS training](../docs/topics/fsrs-training/fsrs-training.md).

```bash
cd ml
python -m pip install -e ".[train,test]"
python -m pytest

# generate a synthetic dataset (reads backend/tempo_demo.sqlite), then fit FSRS-6 on it
python -m tempo_ml.simulator.generate --config configs/multiplicative-memory.json --out data/<name>
python -m tempo_ml.fsrs.train --data data/<name> --out experiments/<date>-<name>/results/binary --seed 7 --target pass --no-personalise
```

- `tempo_ml/catalog.py`: reads the opening catalog from `backend/tempo_demo.sqlite`.
- `tempo_ml/fsrs/`: the vectorised FSRS-6 model and input layout (`model.py`) and the L-BFGS-B trainer (`train.py`, target pass/fail or true recall).
- `tempo_ml/simulator/`: virtual players. `clients.py` archetypes, per-player spread and the client; `memory/multiplicative.py` their hidden memory; `recall.py` per-move recall, retries and move times; `practice.py` repertoire, new lines and scheduling; `grading.py` Again/Hard/Good/Easy and the session record; `generate.py` writes a dataset.
- `tempo_ml/evaluate/`: `metrics.py` (log-loss, Brier, calibration, AUC, error against the true chance) and `days.py` (error in days to 90%).
- `configs/`: generator settings; `multiplicative-memory*.json` are those of the 2026-11-13 run.
- `experiments/<date>-<name>/`: one folder per run; `SUMMARY.md` is its record, scripts that belong only to it sit beside it.
- `tests/`: `test_simulator.py`, `test_memory_models.py`, `test_trainers.py`, `test_metrics.py`.
- `data/`: generated datasets, ignored by Git; each experiment's `dataset_MANIFEST.txt` says how to rebuild them.
- `ml_1000bots/`: the 1,000-client simulator, its opening library build and its first training run, not yet moved into this layout; see its own README.
