# tempo_v1 training parameters

This document records every parameter used for the training run on
`data/tempo_v1` (2026-11-11). It has two parts:

- **Data generation parameters**: what the synthetic players look like
  (from `data/tempo_v1/config.json`)
- **Training parameters**: how the optimizer learns (py-fsrs 6.3.2
  `Optimizer` defaults)

The synthetic player model follows the team records
`docs/topics/synthetic-clients/record.md` and
`docs/topics/review-dataset/record.md`.

---

## 1. Data generation parameters

Command:

```bash
python generate.py --out data/tempo_v1 --config configs/tempo_v1.json
```

### 1.1 General

| Parameter | Value | Meaning |
|---|---|---|
| `seed` | 7 | Random seed: the same seed always produces the same data |
| `n_agents` | 1000 | Number of synthetic players |
| `horizon_days` | 180 | Number of simulated days |
| `start_date` | 2026-01-05 | First simulated day |
| `train_frac` | 0.8 | 80% of players for training (800), 20% for validation (200); **split by player** |

### 1.2 Archetypes (from the team record, one third each)

| Parameter | fast | balanced | diligent | Meaning |
|---|---|---|---|---|
| `baseline_ms` | 220 | 300 | 380 | Motor/UI latency floor (ms): time needed even without thinking |
| `mu` | −0.6 | −0.2 | 0.3 | Centre of the log-normal thinking time (log seconds); higher = slower |
| `sigma` | 0.45 | 0.40 | 0.35 | Spread of the thinking time |
| `beta` | 0.4 | 1.0 | 2.2 | Extra hesitation under weak memory: `exp(beta × (1 − R))` |
| `alpha` | 0.35 | 0.25 | 0.20 | Practice speed-up: `1 / (1 + alpha × reps)` |
| `C` | 0.65 | 0.50 | 0.35 | Forgetting-curve shape (= w20); higher = faster forgetting |
| `init_stability_mult` | 1.0 | 1.0 | 1.0 | Initial memory strength after learning (1.0 = unchanged) |
| `growth_shift` | 0 | 0 | 0 | Memory growth per successful review (0 = unchanged) |

### 1.3 Individual differences

| Parameter | Value | Meaning |
|---|---|---|
| `weight_noise` | 0.15 | Each player's 21 memory weights vary by about ±15% around the archetype |
| `trait_jitter` | 0.10 | Each player's behaviour traits vary by about ±10%; baseline clipped to 150–500 ms, alpha to 0.1–0.5 |
| `freeze_short_term_weights` | true | w17–w19 stay at default (no same-day reviews in the data) |

### 1.4 Openings

| Parameter | Value | Meaning |
|---|---|---|
| `openings_file` | `openings/lichess_openings_classified.csv` | Classified Lichess opening library |
| `n_openings` | 300 | 300 lines drawn at random from the library |
| `user_moves` | 4–16 | Only lines where the player makes 4 to 16 moves |
| (rule) | | The player studies the family's `family_side`; "both" families get a random side |

### 1.5 Study habits

| Parameter | Value | Meaning |
|---|---|---|
| `lines_per_agent` | 15–40 | Lines each player plans to learn |
| `new_line_prob` | 0.15–0.40 | Chance of learning a new line on a study day |
| `skip_day_prob` | 0.05–0.35 | Chance of not studying at all on a day |
| `break_prob` | 0.015 | Chance per day that a break starts |
| `break_days` | 4–30 | Length of a break (days) |
| `desired_retention` | 0.80–0.95 | App's target: schedule a review when recall drops to this level |
| `max_reviews_per_day` | 15 | Daily review cap (most overdue first) |
| `learn_grade` | 3 | A newly learned line is always logged as Good |

The app schedules with the **default weights** (phase 1), not with the
player's true weights.

### 1.6 Recall and grading

| Parameter | Value | Meaning |
|---|---|---|
| `recall_mode` | `line` | Recall is decided once per line (our addition, see below) |
| (fixed rule) | | Any wrong move → **Again (1)** |
| `easy_ms` | 500 | Clean session with mean delay per move (total time ÷ moves − baseline) < 0.5 s → **Easy (4)** |
| `hard_ms` | 1800 | > 1.8 s → **Hard (2)**; 0.5–1.8 s → **Good (3)** |
| (practice count) | | Clean session +1; any mistake −2 (not below 0) |

**Why `line`:** with every move decided separately with probability R (as
the team record is written), a test run gave 93% Again and 264 reviews per
player in six months (40 with `line`), and the true weights could no longer
be used to check the training result.

### 1.7 Generated data

| Item | Value |
|---|---|
| Rows | 121,532 (23,927 new lines, 97,605 reviews) |
| Reviews per player | median 90 |
| Grade mix | Again 15.3%, Hard 10.1%, Good 59.5%, Easy 15.1% |
| Time per move | median 1.17 s |

The dataset is locked: files are read-only, and `data/tempo_v1/MANIFEST.txt`
lists a sha256 fingerprint for every file.

---

## 2. Training parameters

Command:

```bash
python fit_global.py data/tempo_v1 runs/2026-11-11-first-training
```

py-fsrs 6.3.2 `Optimizer`, all defaults:

| Parameter | Value | Meaning |
|---|---|---|
| Training data | 800 training players, 98,161 rows | The 200 validation players are never used |
| Starting point | Default FSRS-6 weights | Optimization starts from the 21 default values |
| `num_epochs` | 5 | Passes over the full data |
| `mini_batch_size` | 512 | Weights are updated every 512 reviews; **with fewer than 512 reviews the optimizer does not train and returns the defaults** |
| `learning_rate` | 0.04 | Step size of each update |
| Optimizer | Adam + cosine annealing | Large steps first, finer steps later |
| `max_seq_len` | 64 | Only the first 64 reviews of each line are used |
| Loss | BCE (= log-loss) | Predicts recall; lower is better |
| Recall label | grade ≠ 1 | Again = forgotten; Hard / Good / Easy = recalled |
| Weight bounds | lower and upper limits | Each weight stays within the FSRS-6 range |
| Timestamps | midnight of each study day | Only whole-day gaps count, not clock time |
| Run time | about 100 s | Apple M4 Mac |

---

## 3. Results

### Fitted weights (`fitted_global.csv`)

| | | | | |
|---|---|---|---|---|
| w0 = 0.2120 | w1 = 1.2931 | w2 = 2.2400 | w3 = 8.2956 | w4 = 5.1221 |
| w5 = 0.7379 | w6 = 3.0686 | w7 = 0.0029 | w8 = 1.6912 | w9 = 0.1478 |
| w10 = 0.8248 | w11 = 1.3189 | w12 = 0.1252 | w13 = 0.3022 | w14 = 1.2226 |
| w15 = 0.6663 | w16 = 1.7311 | w17 = 0.4774 | w18 = 0.2912 | w19 = 0.0658 |
| w20 = 0.4280 | | | | |

- w0, w1, w3 and w19 cannot be learned from this data and stay at default;
  w17 and w18 are only weakly learned.
- **These weights come from synthetic players and only show that the method
  works.** Retrain on real user data once the app is live.

### Validation scores (200 unseen players)

| Weights | log-loss (lower is better) | RMSE (lower is better) | AUC (higher is better) |
|---|---|---|---|
| Default | 0.3930 | 0.0335 | 0.670 |
| **Fitted** | **0.3910** | **0.0201** | 0.670 |
| Oracle (true weights) | 0.3849 | 0.0126 | 0.692 |

- **log-loss**: penalty for each prediction; confident wrong predictions cost the most.
- **RMSE**: calibration. When the model says "85% will pass", does about 85% pass?
- **AUC**: ranking. Can the model put passes above failures? 0.5 = random guessing.

The fitted weights close about **25%** of the default-to-oracle gap (95%
bootstrap interval 11%–37%). The decay C moves from 0.15 (default) to 0.43
(true median 0.49). See `SUMMARY.md` and `analysis.txt` in
this folder for details.
