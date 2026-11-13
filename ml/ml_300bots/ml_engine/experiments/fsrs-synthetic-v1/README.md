# Experiment: FSRS-6 trained on synthetic clients (v1)

## Protocol (written before the run)

**Question.** Fitted on synthetic-client sessions over real opening lines, does
FSRS-6 predict whether a held-out player plays a line cleanly better than
FSRS-6 with its default parameters? Does per-player fine-tuning improve it
further?

**Kind.** Exploratory investigation and the first training run of the ML
engine's FSRS component. No pass/fail bar is fixed; the review planner is not
trained here (its design is not decided).

**Decision it informs.** Whether the general model starts from trained or
default FSRS parameters, and whether per-player fine-tuning is worth building
into the ML controller.

**Data.** `python -m tempo_ml.synthetic_data.generate --out data --seed 20261111`
(100 clients per archetype, 180 days, the opening library at
`openings/opening_lines.csv`). The generator's practice policy, trait spread and
outputs are documented in `ml_engine/src/tempo_ml/synthetic_data/generate.py`.

**Training and evaluation.** `python -m tempo_ml.fsrs.train --data data --out results --seed 7`,
protocol in `ml_engine/src/tempo_ml/fsrs/train.py`:
clients split per archetype into fit 70 % / validation 10 % / test 20 %;
FSRS-6 fitted by L-BFGS-B on mean binary cross-entropy (success = grade > 1)
over tested reviews at least one day apart; test metrics are log loss, Brier
score, AUC and MAE against the hidden true clean-session probability.
Baselines: FSRS-6 defaults, and a constant equal to the fit clients' success
rate. Personalisation: per client, first 60 % of tested reviews fine-tune, last
40 % evaluate; the L2 pull strength is chosen on validation clients only.

**Budget and stopping.** One generation and one training run, under 30 minutes
of CPU in total. No setting is changed after seeing test results; a changed
setting would be a new, recorded attempt.

## Attempts before this run

- Probe of the generator (15 clients): 81 % of sessions graded Again. Cause: a
  lapse could cut stability to 0.1 day, and a clean session needs every move,
  probability R^M, so lapsed lines never recovered. Change: the lapse floor
  (`MultiplicativeStability.min_days`) became 1.0 day (a freshly learned
  line). Re-probe with 30 clients: 35 % lapses, rising with t/S from 6 % to
  73 %. This happened before any training.

## Results

Run on 2026-11-11 in Claude's cloud workspace (Python 3.13.18, numpy 2.5.3,
scipy 1.18.1, pandas 3.0.5, Linux, 2 CPUs). Code was not committed to git, so
there is no source pin; `data/manifest.json` holds SHA-256 hashes of the inputs
and outputs. The data CSVs are git-ignored and can be regenerated from the seed.
Raw results: `results/metrics.json`, `results/personalisation_test_clients.csv`,
log `results/results_log.txt`. Generation took 5 s; training took 997 s (general fit 279 s).

**Data.** 300 clients, 119,517 sessions (8,129 Learning Mode sessions, 111,388
Repeating Mode sessions), 90,357 tested reviews spaced at least 1 day apart.
Split: fit 210 clients / 62,053 reviews, validation 30 / 9,366, test 60 / 18,938.

**General model, test clients (18,938 reviews).**

| Predictor | Log loss | Brier | AUC | MAE vs true p_clean |
|---|---|---|---|---|
| Constant (fit success rate) | 0.670 | 0.239 | 0.500 | 0.229 |
| FSRS-6 default parameters | 0.692 | 0.233 | 0.709 | 0.206 |
| FSRS-6 trained | **0.540** | **0.182** | **0.788** | **0.104** |

Mean predicted success: 0.615 trained vs 0.779 default; observed 0.609.
Test log loss per archetype, trained vs default: balanced 0.549 vs 0.700,
blitzer 0.571 vs 0.765, diligent 0.501 vs 0.609. The optimiser converged
after 208 iterations; fitted parameters are in `results/fsrs6_general_parameters.json`.

**Personalisation.** On validation clients, fine-tuning was worse than the
general model at every pull strength (λ = 0.01, 0.1, 1, 10 gave log loss 0.495,
0.489, 0.483, 0.476 vs 0.464 general). The best λ (10) applied to test clients'
late reviews: general 0.445, personalised 0.448, default 0.510; 29 of 60
clients improved.

**Interpretation.** Trained FSRS-6 clearly beats the defaults on synthetic
clients, which are harder than default FSRS assumes (default over-predicts
success by 17 points): a line is only clean if every one of its M moves is
recalled. Per-player fine-tuning of all 21 parameters on about 190 reviews per
player does not help here. A likely reason is that the population is close to
three archetypes, so the general model already fits each player; per-player
differences would need either more history per player or tuning fewer
parameters. These are findings on synthetic data from one generator and one
seed; they say nothing yet about human players.

**Hold-out benchmark on new clients (added after the run).** 60 new clients
(20 per archetype) generated with a different seed
(`generate --out holdout_data --seed 20261112 --clients-per-archetype 20`),
scored without any refitting by `python -m tempo_ml.fsrs.benchmark` →
`results/holdout_benchmark.json`. 18,543 reviews, observed success 61.9 %.

| Predictor | Log loss | Brier | AUC | MAE vs true p_clean | Mean prediction |
|---|---|---|---|---|---|
| Constant guess (62.9 %) | 0.665 | 0.236 | 0.500 | 0.233 | 62.9 % |
| FSRS-6 default | 0.684 | 0.229 | 0.709 | 0.205 | 78.5 % |
| FSRS-6 trained | **0.533** | **0.179** | **0.792** | **0.105** | 61.8 % |

These match the original test split, so the trained weights carry over to new clients.

**Next step.** Decide the review planner design; for personalisation, try
fine-tuning a few parameters (for example w[20] decay and initial stability)
instead of all 21.
