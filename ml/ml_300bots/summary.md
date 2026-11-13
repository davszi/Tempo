# Summary: synthetic clients, synthetic dataset and FSRS-6 training

## What was built

| Part | Location | What it does |
|---|---|---|
| Synthetic clients | `ml_engine/src/tempo_ml/synthetic_clients/` | Simulated players with cognitive traits (baseline, μ, σ, β, α, C) and three personas: blitzer, balanced, diligent. They run Learning Mode and Repeating Mode sessions and output move accuracy and hesitation time. |
| Session schema and grading | `ml_engine/src/tempo_ml/review_dataset/` | The CSV format and the Again/Hard/Good/Easy grading function. |
| Opening library | `openings/` | 3,865 real Lichess lines with side labels and move counts. |
| Dataset generator | `ml_engine/src/tempo_ml/synthetic_data/` | Runs the clients over real lines for 180 days and writes the dataset. |
| FSRS-6 trainer | `ml_engine/src/tempo_ml/fsrs/` | FSRS-6 in numpy, fitted with scipy (no PyTorch needed); formulas checked against the official `fsrs` package. |
| Benchmark | `ml_engine/src/tempo_ml/fsrs/benchmark.py` | Scores the default and trained weights on a new dataset, with no retraining. |
| Experiment | `ml_engine/experiments/fsrs-synthetic-v1/` | The generated data, the trained weights and the full results. |

Tests: 34 unit tests, all passing.

## Dataset

- 300 synthetic clients (100 per persona), each playing white or black, each learning 15–40 real lines.
- 119,517 sessions, of which 90,357 are tested reviews at least 1 day apart.
- Split by client: 210 for training, 30 for validation (held out, not used in this run), 60 for testing.

## What is predicted

Before each review, the model predicts **p**: the chance the player plays the whole line without a mistake.
The real outcome is **y = 1** (clean session, grade 2–4) or **y = 0** (at least one blunder, grade 1).

FSRS computes p from the line's memory stability S and the days t since the last review:

$$p = R(t, S) = \left(1 + F \cdot \frac{t}{S}\right)^{-w_{20}}, \qquad F = 0.9^{-1/w_{20}} - 1$$

S and the line's difficulty are updated after every review using the 21 FSRS weights w₀…w₂₀.

## Loss functions

**Training loss: binary cross-entropy (log loss),** averaged over all tested reviews:

$$L(w) = -\frac{1}{N}\sum_{i=1}^{N} \Big[ y_i \log p_i + (1 - y_i)\log(1 - p_i) \Big]$$

It punishes confident wrong predictions heavily. Minimised with L-BFGS-B, keeping each weight within the official FSRS bounds.

**Evaluation metrics on test clients:**
- **Log loss**: as above; lower is better.
- **Brier score**: the mean of (p − y)²; lower is better.
- **AUC**: how well the model ranks reviews from likely-to-fail to likely-to-pass; 0.5 = no skill, 1.0 = perfect.
- **MAE vs truth**: the mean |p − p_true|, where p_true is the clients' hidden true chance of a clean session (known only because the data is synthetic); lower is better.

## Benchmarks (60 test clients, 18,938 reviews)

The three predictors compared:
- **Constant guess**: always predicts the training clients' average success rate (62.9%). A minimum bar.
- **FSRS default**: FSRS-6 with its standard weights (learned from flashcard users).
- **FSRS trained**: FSRS-6 with weights fitted on the synthetic training clients.

| Predictor | Log loss ↓ | Brier ↓ | AUC ↑ | MAE vs truth ↓ | Mean prediction |
|---|---|---|---|---|---|
| Constant guess | 0.670 | 0.239 | 0.500 | 0.229 | 62.9% |
| FSRS default | 0.692 | 0.233 | 0.709 | 0.206 | 77.9% |
| **FSRS trained** | **0.540** | **0.182** | **0.788** | **0.104** | **61.5%** |

Actual success rate on the test clients: 60.9%.

Log loss by persona (trained vs default): balanced 0.549 vs 0.700, blitzer 0.571 vs 0.765, diligent 0.501 vs 0.609.

### Hold-out benchmark: 60 brand-new clients

60 new synthetic clients (20% of the original 300; 20 per persona), generated with a different seed (20261112), so none were seen in training or validation. Each was scored with the default weights and the trained weights, with no retraining. 18,543 reviews; actual success rate 61.9%.

| Predictor | Log loss ↓ | Brier ↓ | AUC ↑ | MAE vs truth ↓ | Mean prediction |
|---|---|---|---|---|---|
| Constant guess | 0.665 | 0.236 | 0.500 | 0.233 | 62.9% |
| FSRS default weights | 0.684 | 0.229 | 0.709 | 0.205 | 78.5% |
| **FSRS trained weights** | **0.533** | **0.179** | **0.792** | **0.105** | **61.8%** |

Log loss by persona (trained vs default): balanced 0.522 vs 0.648, blitzer 0.580 vs 0.793, diligent 0.495 vs 0.602.
The results match the original test split, so the trained weights carry over to new players.

```bash
python -m tempo_ml.synthetic_data.generate --out experiments/fsrs-synthetic-v1/holdout_data --seed 20261112 --clients-per-archetype 20
python -m tempo_ml.fsrs.benchmark --data experiments/fsrs-synthetic-v1/holdout_data --weights experiments/fsrs-synthetic-v1/results/fsrs6_general_parameters.json --base-rate 0.6289 --out experiments/fsrs-synthetic-v1/results/holdout_benchmark.json
```

## Conclusions

- Training works: the trained weights cut the error against the true recall chance in half compared with the default weights.
- The default weights are too optimistic, because a chess line needs every move right, which makes it harder than a single flashcard.
- Not done yet: the review planner (its design is still undecided) and any testing on real players.

## Changes made along the way

- A test run showed lines that lapsed could never recover (81% failed sessions). The rule was changed so a blunder never makes a line weaker than a freshly learned one (1-day stability), before any training ran.
- Clients track lines by ID, because 688 opening names appear more than once.

## Reproduce

```bash
cd ml_engine
pip install -e ".[train,test]"
python -m tempo_ml.synthetic_data.generate --out experiments/fsrs-synthetic-v1/data --seed 20261111
python -m tempo_ml.fsrs.train --data experiments/fsrs-synthetic-v1/data --out experiments/fsrs-synthetic-v1/results --seed 7
```
