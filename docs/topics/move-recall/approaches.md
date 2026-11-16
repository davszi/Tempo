# Training approaches for per-move recall

## 1. Scope

This record describes the two ways of fitting FSRS weights whose recall
means one player move, decided on 2026-11-16 to be trained side by side
(arms A1c-acc and A1c-pass in the
[move recall record, section 3.4](move-recall.md#34-training-arms)). Terms
(`M`, `k`, `L(M)`, `R`, `p_pass`, accuracy) are defined in
[section 2 of that record](move-recall.md#2-terms). Both approaches are
specified, not implemented; no results exist yet.

## 2. What the two approaches share

- **FSRS state replay.** Each player/line is one card. Stability and
  difficulty are replayed review by review from the grades
  (Again/Hard/Good/Easy) of the decided grading rule, with the app's clock,
  exactly as in the line-level arms. The grade drives the memory update; the
  training target only enters the loss.
- **What FSRS recall means.** The fitted `R` before a review is the chance
  of recalling one move of the line.
- **Scheduling and scoring.** Both predict the pass chance
  `p_pass(R, M)`, are scheduled at the per-move target `R*(M)`, and are
  scored against the same pass labels and hidden pass chance as the
  line-level arms ([move recall record, sections 3.3 and 3.5](move-recall.md#33-the-scheduler-targets-a-09-pass-chance)).
- **Trainer.** Both use the shared L-BFGS-B trainer
  (`ml/tempo_ml/fsrs/train.py`); py-fsrs's Optimizer cannot express either
  loss. As in the current arms, Learning sessions update the state but are
  excluded from the loss.

They differ only in what the loss compares `R` with.

## 3. Approach 1: accuracy target

**Target.** The accuracy of the review, `a = (M − k) / M`, already exported
as `accuracy`.

**Loss** for one review, with fitted per-move recall `R`:

```text
loss = −[ a · log R + (1 − a) · log(1 − R) ]
```

This is binary cross-entropy with a fractional target. Its expected value
is minimized at `R = E[a]`, the mean per-move recall of the review. With
the weight `M` it becomes

```text
M · loss = −[ (M − k) · log R + k · log(1 − R) ]
```

which is the negative log-likelihood of `k` mistakes under the binomial,
up to a constant. Unweighted, every review counts the same; weighted, every
move counts the same. The choice is open
([move recall record, section 7.1](move-recall.md#71-loss-weighting-for-the-accuracy-target)).

**Example.** A 6-move line, one mistake (`k = 1`, a pass under the decided
rule). The target is `a = 5/6 = 0.83`. A review with no mistake has target
1.0, one with two mistakes 0.67.

**Strengths.**

- Uses the number of mistakes, not only pass or fail. Fisher information
  about `R` in one review (design arithmetic,
  [evidence script](evidence/2026-11-16-pass-chance-arithmetic/pass_chance_arithmetic.py),
  part 3):

  | Moves | Mistake count / pass bit, R = 0.90 | R = 0.97 |
  |---|---|---|
  | 3 | 1.12 | 1.03 |
  | 6 | 1.74 | 4.00 |
  | 10 | 2.45 | 13.83 |
  | 14 | 3.37 | 48.16 |

  The gain is largest for long lines and for lines a player knows well,
  where almost every review passes and a pass says little.
- `E[a]` equals the mean per-move recall whether or not mistakes cluster,
  because an expectation needs no independence. The fitted weights estimate
  per-move recall without the binomial assumption.
- Independent of the mistake limits: if `L(M)` changes, the weights stay
  valid and only `R*(M)` is recomputed.

**Weaknesses.**

- If real mistakes cluster, the fitted mean recall is right, but the pass
  chance derived from it with the binomial `p_pass` is too high, so the
  scheduler's 0.9 pass target is missed. The error sits in `R*(M)`, not in
  the weights ([move recall record, section 7.3](move-recall.md#73-checking-the-binomial-assumption-on-real-reviews)).
- Fits the moves, not the quantity the app schedules on.

## 4. Approach 2: pass-chance target

**Target.** The pass label `y = 1` if `grade > 1` (at most `L(M)`
mistakes), else 0.

**Loss** for one review:

```text
q    = p_pass(R, M) = Σ_{k=0..L(M)} C(M,k) (1 − R)^k R^(M−k)
loss = −[ y · log q + (1 − y) · log(1 − q) ]
```

**Example.** The same 6-move line with one mistake has `y = 1`, the same as
a review without mistakes. The loss compares 1 with
`q = R^6 + 6 R^5 (1 − R)`.

**Strengths.**

- Fits the quantity the app schedules on, with the team's definition of a
  pass.
- If real mistakes cluster, the fit bends `R` so that `p_pass(R, M)` still
  matches observed pass rates. The predicted pass chance then stays
  calibrated even though the binomial link is wrong, although `R` no longer
  means a clean per-move recall.

**Weaknesses.**

- One bit per review: the number of mistakes is discarded (table in
  section 3).
- The link uses `L(M)`, so changing the mistake limits requires refitting.
- Uses the binomial assumption in training as well as in scheduling.

## 5. Side by side

| | Approach 1: accuracy | Approach 2: pass chance |
|---|---|---|
| Target per review | `(M − k)/M` | 1 if `k ≤ L(M)`, else 0 |
| Prediction compared with the target | `R` | `p_pass(R, M)` |
| Information per review | Number of mistakes | Pass or fail |
| Binomial assumption used in | Scheduling only | Training and scheduling |
| Depends on `L(M)` | No | Yes |
| If real mistakes cluster | `R` stays the mean move recall; the scheduled pass chance is too high | The predicted pass chance stays calibrated; `R` loses its per-move meaning |
| py-fsrs Optimizer | Cannot | Cannot |

## 6. Expectations and how they are tested

In the simulator, moves are drawn independently, so both approaches are
correctly specified and Approach 1 is expected to fit at least as well,
with the difference growing with line length and with fewer reviews per
player. This is a prediction, not a result. The retraining compares both
with each other and with the line-level arms A1 and A1c on the same pass
labels and hidden pass chance; the experiment's `PLAN.md` states what
counts as a difference. Which approach suits real players depends on
whether their mistakes cluster, which only real reviews can show
([move recall record, section 7.3](move-recall.md#73-checking-the-binomial-assumption-on-real-reviews)).

## 7. Where the pass chance enters

Both approaches predict and are judged by the pass chance; they differ only
in what the training loss compares.

| Stage | Approach 1: accuracy (A1c-acc) | Approach 2: pass chance (A1c-pass) |
|---|---|---|
| Training: what the loss compares | `R` with the accuracy `(M − k)/M` | `p_pass(R, M)` with the pass label |
| Scheduling: when a line is due | `p_pass(R, M)` falls to 0.9 | the same |
| Evaluation: what is scored | `p_pass(R, M)` against the pass labels and the hidden pass chance | the same |

Approach 1 never computes the pass chance while it fits; it is trained on
accuracy and judged on the pass chance. The line-level arms A1 and A1c are
scored against the same pass labels and hidden pass chance with their
line-level `R`. The comparison therefore asks whether the information in
the mistake count gives better pass-chance predictions than training on
the pass label directly.

**Pass chance, worked once.** A 6-move line has the limit `L(6) = 1`. At
per-move recall `R = 0.9`: no mistake `0.9^6 = 0.531`, exactly one mistake
`6 · 0.9^5 · 0.1 = 0.354`, so `p_pass(0.9, 6) = 0.886`.

## 8. Compared with the 2026-11-13 arms A2 and B2

The arms A2 and B2 of the 2026-11-13 experiment
([FSRS training record](../fsrs-training/fsrs-training.md#multiplicative-memory-arms-a2-and-b2))
used multiplicative memory and the earlier grading rule, under which a
pass meant a review without mistakes. In both, FSRS recall meant the whole
line:

| | A2 | B2 |
|---|---|---|
| Target | pass/fail of the review (pass = no mistakes) | hidden true chance of a clean review, `R^M` |
| Loss | log-loss | MSE |
| Available for real players | yes | no: `R^M` exists only in the simulator |
| Information per review | one bit | the hidden chance itself |

Under the earlier rule the clean-review chance `R^M` decays faster on longer
lines, so one FSRS curve cannot fit all line lengths with one set of
weights ([move recall record, section 3.2](move-recall.md#32-fsrs-recall-means-one-move)).
The per-move arms put the line length in `p_pass(R, M)` instead of in the
weights.

The same review gives each arm a different target. Example: a 6-move line
with one mistake.

| Arm | Target of this review | What it says |
|---|---|---|
| A2 | 0 | failed, although 5 of 6 moves were right |
| B2 | the hidden `R^6`, for example 0.531 at `R = 0.9` | the true clean chance; simulator only |
| A1c-pass | 1 | passed, the same label as a review without mistakes |
| A1c-acc | 5/6 = 0.83 | the share of moves recalled |

The accuracy target is the observable counterpart of B2's hidden target:
its expected value is the per-move recall `R` (section 3), and it is
exported for bots and real players alike.
