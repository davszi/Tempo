# tempo_ml

TEMPO ML engine package. Specification and implementation status:
`docs/topics/synthetic-clients/record.md` (section 6).

```bash
cd ml_engine
python -m pip install -e ".[train,test]"
python -m pytest

# generate a synthetic dataset, then fit FSRS-6 on it
python -m tempo_ml.synthetic_data.generate --out experiments/<name>/data --seed 20261111
python -m tempo_ml.fsrs.train --data experiments/<name>/data --out experiments/<name>/results --seed 7
```

- `tempo_ml.synthetic_clients`: simulated players.
- `tempo_ml.openings`: loads the opening library in `openings/`.
- `tempo_ml.synthetic_data`: runs clients over real lines and writes the session dataset.
- `tempo_ml.fsrs`: FSRS-6 in numpy, fitting with scipy, evaluation and per-player fine-tuning.
- `experiments/fsrs-synthetic-v1/`: first dataset and training run.
