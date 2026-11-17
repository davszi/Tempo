# Move Recall Model

## 1. Scope and status

This record holds the decisions on **what FSRS recall means in TEMPO**: the
chance of recalling one player move, with the chance of passing a whole line
derived from it under the [session grading rule](../session-grading/session-grading.md).
It also holds the scheduling target, the training arms and the evaluation
that follow from that meaning. The two training approaches are described in
[Training approaches](approaches.md).

| Item | Owner |
|---|---|
| Meaning of recall, scheduling target, training arms, decisions and rationale | this record |
| The two training targets, their losses and their trade-offs | [Training approaches](approaches.md) |
| Mistake limits `L(M)` and grades | [Session grading record](../session-grading/session-grading.md) |
| Hidden memory and per-move draws in the simulator | [Synthetic-client record](../synthetic-clients/record.md) |
| Fitting, metrics and dated results | [FSRS training record](../fsrs-training/fsrs-training.md) |
| Runtime scheduling in the app | [System architecture record](../system-architecture/system-architecture.md) |

**Status (2026-11-16): decided; implemented in the simulator, training and
evaluation; the app's per-length scheduling is not implemented.** The decisions in section 3 were taken on
2026-11-16 by the ML owner. The ML implementation (section 6) landed the
same day; the retraining is the experiment
[`ml/experiments/2026-11-16-move-recall/`](../../../ml/experiments/2026-11-16-move-recall/PLAN.md).
The app grades with the decided rule (`52e9535`) but still schedules on
line-level FSRS recall. Section 7 lists what is still open.

This record answers the unresolved choice in the
[move/line recall proposal](../../open/recall-target-mismatch.md): the
observation model includes line length and per-move behavior explicitly.

## 2. Terms

| Term | Definition |
|---|---|
| `M` | Player moves in the line, as in the session grading record. |
| `k` | Mistakes in a review: player moves whose first attempt was wrong. |
| `L(M)` | Mistake limit: 0 for `M ≤ 3`, 1 for 4–7, 2 for 8–12, 3 for 13 or more ([session grading, section 3.2](../session-grading/session-grading.md#32-mistake-limits-by-line-length)). |
| Per-move recall `R` | FSRS retrievability of one player move of the line: `R(t) = (1 + F·t/S)^(−C)`, `F = 0.9^(−1/C) − 1`. |
| Pass | A review with `k ≤ L(M)`, i.e. grade Hard, Good or Easy. Training label `grade > 1`. |
| Pass chance `p_pass(R, M)` | `Σ_{k=0..L(M)} C(M,k) (1−R)^k R^(M−k)`: the chance of at most `L(M)` mistakes when each move is recalled independently with probability `R`. |
| Accuracy | `(M − k) / M`, the share of moves right on the first attempt. Already exported as `accuracy` ([review dataset, section 2](../review-dataset/record.md)). |
| Per-move target `R*(M)` | The `R` at which `p_pass(R*, M) = 0.9`. |

## 3. Decisions

All decided 2026-11-16.

### 3.1 FSRS memory is the only hidden memory model

The simulator keeps only the FSRS-6 hidden memory
(`ml/tempo_ml/simulator/memory/fsrs.py`) and becomes its default. The
multiplicative memory model, its configs and tests are removed; the
2026-11-13 experiment that used it stays as a historical record, and the
code stays retrievable from Git at the commit that removes it.

Rationale: one memory model to keep consistent with the new grading rule.
FSRS memory updates by grade, so the open question of how memory changes
after a passed review with mistakes
([session grading, section 6.1](../session-grading/session-grading.md#61-memory-update-for-a-passed-review-with-mistakes))
has an answer there: Hard, Good and Easy are successes with their grade's
update; only Again is a lapse.

### 3.2 FSRS recall means one move

FSRS weights fitted by the new arms (section 3.4) describe the recall of
one player move. The chance of passing a line is derived from it with
`p_pass(R, M)`.

Rationale: under the new grading rule the line pass chance has a shape the
FSRS forgetting curve cannot draw, while per-move recall has exactly that
shape. Design arithmetic for one player (C = 0.5, S = 10 days, 0–40 days;
[evidence script](evidence/2026-11-16-pass-chance-arithmetic/pass_chance_arithmetic.py),
part 2):

| Curve fitted by one FSRS curve | 3 moves | 6 moves | 10 moves | 14 moves |
|---|---|---|---|---|
| No-mistake chance `R^M` (earlier rule) | exact, C = 1.5 | exact, C = 3.0 | exact, C = 5.0 | exact, C = 7.0 |
| New-rule pass chance | exact | max error 0.051 | max error 0.086 | max error 0.112 |
| Per-move recall | exact, C = 0.5 | exact, C = 0.5 | exact, C = 0.5 | exact, C = 0.5 |

Under the earlier rule the shape fits but the decay grows with line length,
so one set of weights cannot fit all lengths. Under the new rule a single
FSRS curve fitted to all four lengths at once misses by up to 0.136 (the
decay reaches its bound of 20); FSRS recall followed by `p_pass` recovers
S = 10 and C = 0.5 with no error. This is arithmetic under the binomial
assumption, not a measurement.

### 3.3 The scheduler targets a 0.9 pass chance

A line is due when its pass chance falls to 0.9:
`p_pass(R, M) = 0.9`, i.e. when per-move recall falls to `R*(M)`. The
target does not depend on the player or the weights, so `R*(M)` is a fixed
table. The app's displayed recall becomes the pass chance
`p_pass(R, M)`; `target_recall` stays 0.9.

`R*(M)` and the interval it gives for the example player
([evidence script](evidence/2026-11-16-pass-chance-arithmetic/pass_chance_arithmetic.py),
part 1; design arithmetic):

| M | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 | 14 | 18 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `L(M)` | 0 | 0 | 0 | 1 | 1 | 1 | 1 | 2 | 2 | 2 | 2 | 2 | 3 | 3 | 3 |
| `R*(M)` | 0.9000 | 0.9487 | 0.9655 | 0.8574 | 0.8878 | 0.9074 | 0.9212 | 0.8531 | 0.8705 | 0.8842 | 0.8952 | 0.9043 | 0.8584 | 0.8691 | 0.8994 |
| Days (C = 0.5, S = 10) | 10.0 | 4.7 | 3.1 | 15.4 | 11.5 | 9.1 | 7.6 | 15.9 | 13.6 | 11.9 | 10.6 | 9.5 | 15.2 | 13.8 | 10.1 |

Rationale: the team's 90% target keeps its meaning, a 90% chance to pass
the line under the decided grading rule. The binomial assumption is used
only here; real reviews can check it directly (section 7.3).

**INVARIANT:** weights fitted on per-move recall and the `R*(M)` scheduler
ship together. Per-move weights in the current line-level scheduler would
schedule 3-move lines at a pass chance of 0.729 and 14-move lines at 0.956;
line-level weights such as `backend/fitted_global.csv` in the new scheduler
are equally wrong. A weights file records which recall it means.

### 3.4 Training arms

Every arm uses FSRS memory, the new grading rule, the current catalog, the
app's clock (whole elapsed days of real timestamps) and the same FSRS state
replay by grade. Arms differ only in the training target and the link from
FSRS recall to the pass chance.

| Arm | Trainer | Target | FSRS recall means | Predicted pass chance | Role |
|---|---|---|---|---|---|
| A1 | py-fsrs Optimizer | pass/fail | the line | `R` | Line-level baseline, the app's current training path |
| A1c | shared trainer | pass/fail | the line | `R` | Line-level baseline on the shared trainer |
| A1c-acc | shared trainer | accuracy | one move | `p_pass(R, M)` | Approach 1 in [Training approaches](approaches.md#3-approach-1-accuracy-target) |
| A1c-pass | shared trainer | pass/fail | one move | `p_pass(R, M)` | Approach 2 in [Training approaches](approaches.md#4-approach-2-pass-chance-target) |

Both per-move approaches are trained; neither is chosen before the results.
py-fsrs cannot train either per-move arm because its loss is fixed. Training
runs on the university cluster through Slurm, with three generated
populations (seeds) of 300 players and 60 test and 60 hold-out players
each; the experiment's `PLAN.md` fixes the protocol before it runs.

### 3.5 Evaluation follows the pass meaning

All arms are scored against the same quantities so that they are comparable:

- **Pass predictions:** each arm's predicted pass chance against the
  `grade > 1` labels (log-loss, Brier, calibration, AUC) and against the
  hidden pass chance `p_pass(R_true, M)`, computed from the hidden per-move
  recall already in `ground_truth.csv` (`retrievability`).
- **Days metric:** true days are the days until the hidden pass chance
  falls to 0.9, `S/F · (R*(M)^(−1/C) − 1)` with the client's hidden S and C.
  A per-move arm predicts the same expression with its fitted S and decay;
  a line-level arm predicts its fitted S. This replaces
  `0.9^(1/M)` in the current `evaluate.days.true_days`
  ([FSRS training, days metric](../fsrs-training/fsrs-training.md#days-metric)),
  which assumes the no-mistake rule.

Days results under the new rule are not comparable with the 2026-11-13 and
2026-11-14 experiments, whose true days used the no-mistake meaning.

## 4. Simulator assumption

The simulator draws every player move of a review with the same per-move
recall `R` of the line, independently
(`SyntheticClient.review`, `ml/tempo_ml/simulator/clients.py`). So the
binomial `p_pass` is exact in simulation by construction. Real players may
make mistakes in clusters, for example after forgetting a branch point;
then `p_pass` overstates the pass chance at a given mean per-move recall.
Simulation therefore cannot show how well either per-move approach handles
real players; section 7.3 says how to check it.

## 5. Rejected alternatives

| Alternative | Why not taken |
|---|---|
| Keep line-level FSRS on pass/fail only (A1, A1c) | The new-rule pass curve has a shape FSRS cannot draw (section 3.2). Kept as baselines. |
| Choose the grading rule so that the pass chance equals per-move recall | No mistake-count rule does it: the binomial tail is steeper than the identity. Near R = 0.9 the decided limits come close (pass chance 0.886, 0.930, 0.956 for 6, 10, 14 moves), but not at 0.8 (0.655, 0.678, 0.698) or 0.98. |
| Schedule on 90% per-move recall | Changes the meaning of the team's 90% target from passing the line to recalling a move. Not taken. |
| Train only one of the two per-move approaches | Their trade-off depends on whether real mistakes cluster, which simulation cannot show (section 4). Both are trained. |

## 6. Implementation targets

The ML rows were implemented on 2026-11-16: `ml/tempo_ml/pass_chance.py`
(`mistake_limit`, `p_pass`, `per_move_target`), the arms of
`tempo_ml.fsrs.train` (`--arm line | pass | accuracy | true-recall`), the
link-aware scoring in `evaluate/metrics.py` and the days metric in
`evaluate/days.py`. The reference `p_pass` and `R*(M)` for the app are
`pass_chance.py` and its tests in `ml/tests/test_metrics.py` (enumeration
of all outcomes, and the section 3.3 table). Of the app rows, the grading
rule and browser timing landed in `52e9535`; per-line scheduling at `R*(M)`
is not started.

| Work | Owner |
|---|---|
| Simulator: new grading rule, lapse only on Again, FSRS memory only ([session grading, section 5.1](../session-grading/session-grading.md#51-simulator-mltempo_mlsimulator)) | ML |
| Training: per-move link `p_pass(R, M)` and the accuracy target in the shared trainer; `R*(M)` and the days metric in `evaluate/` | ML |
| Retraining of the four arms on the cluster as a new dated experiment | ML |
| A reference `p_pass` and `R*(M)` implementation with test vectors for the app | ML |
| App: per-line scheduling at `R*(M)` (for example one py-fsrs `Scheduler` per line length with `desired_retention = R*(M)`), the line's `M` in `schedule_review` and `memory`, displayed recall as `p_pass` | App team |
| App: the new grading rule and browser timing ([session grading, section 5.3](../session-grading/session-grading.md#53-app-backend-frontend)) | App team |

The app changes for scheduling are needed only if a per-move arm is chosen
for the shipped weights.

## 7. Open items

### 7.1 Loss weighting for the accuracy target

Decided 2026-11-16: weighted by `M`, which equals the binomial likelihood of
`k`, so every move counts the same. See
[Training approaches](approaches.md#3-approach-1-accuracy-target).

### 7.2 Reference arms

Decided 2026-11-16 and part of the experiment: a simulator-only arm A1c-R
trained on the hidden per-move recall (an upper reference for the per-move
curve, as B1 was for the line-level curve), and a reduced-data run (the
first 60 of 180 days), where the two approaches are expected to differ most.

### 7.3 Checking the binomial assumption on real reviews

Once the app records `M` and `k`
([session grading, section 6.3](../session-grading/session-grading.md#63-exported-inputs)):
compare the observed pass rate of reviews at their due date with 0.9 by
line length, and the distribution of `k` with the binomial at the fitted
`R`. If mistakes cluster, correct `R*(M)` from data; the per-move weights
need not change.

### 7.4 Which weights ship

A team decision, together with the app's scheduler change. Input from the
retraining (section 8): either per-move arm, not a line-level arm; the two
per-move arms did not differ on simulated clients.

## 8. Results (2026-11-16)

The [move-recall experiment](../../../ml/experiments/2026-11-16-move-recall/SUMMARY.md)
trained the four arms of section 3.4 plus the reference A1c-R on three
simulated populations. Per-move recall predicted the pass outcome better
than line-level recall in every population and on hold-out: against a
perfect predictor the per-move arms closed 80–81% of the gap from the
FSRS-6 defaults, the line-level arms 33–34%. A1c-pass and A1c-acc did not
differ, also with 60 of 180 days of history, so the expectation in
[training approaches, section 6](approaches.md#6-expectations-and-how-they-are-tested)
was not borne out. The line-level arms predicted about the same pass rate
for every line length, while the observed rate jumps where one more mistake
is allowed; the per-move arms followed it. Numbers, attempts and limits are
in the run's summary; simulated clients only.
