# Proposal: estimate personal FSRS weights with a neural network

Status: proposed, not accepted for implementation or deployment. The user
requested saving this proposal on 2026-11-15. Saving it does not authorize
training, changing the runtime model or replacing shipped weights.

Owner: this document holds the prospective design, comparison and unresolved
choices. [FSRS Training](../topics/fsrs-training/fsrs-training.md) remains the
owner of implemented fitting and dated evidence;
[Synthetic Players](../topics/synthetic-clients/record.md) owns the generators.

## Question and rationale

Can a small neural network use a player's earlier practice history to produce
FSRS-6 parameters that predict later reviews better than the current global
fit and regularized independent personal fits?

The hypothesis is that similar histories can share statistical strength,
especially when an individual has little data. Improvement is unmeasured.
The model would estimate parameters; FSRS would still update memory state and
calculate intervals. The [mechanism diagram](neural-fsrs-weights.mmd) separates
weight estimation, replay and evaluation.

This adapts the parameter-generating idea in
[Ha, Dai and Le, HyperNetworks (2016)](https://arxiv.org/abs/1609.09106).
That paper does not establish this particular FSRS application. If the goal
is only one global vector, direct gradient-based optimization of its 21
parameters is a simpler alternative worth comparing before adding a network.

## First candidate

- Inputs: observed-history summaries available before a fixed cutoff:
  history size, grade frequencies, review-gap distribution, lapse rate,
  learning/review mix and line lengths, with missing-value indicators.
  Fit normalization on training players only. The exact feature schema and
  units must be fixed before the confirmatory comparison.
- Network: one hidden layer, initially 32 units, outputting corrections around
  the fitted global vector. These are proposed settings, not tuned results.
- Output: one 21-parameter FSRS-6 vector per player. Use a bounded transform
  matched to the pinned model's bounds, regularization toward the global
  vector, and a global fallback for new or insufficient-history players.
  Bounds alone do not prove valid scheduling behavior; verify state and
  interval invariants against the pinned runtime too.
- Training: differentiate through an equivalent implementation of the existing
  FSRS recurrence. Minimize binary cross-entropy against later unassisted
  session success, plus the regularizer. This learns from observed outcomes,
  not from the simulator's original weights or hidden recall probabilities.
- Scope: hold the vector fixed throughout each evaluated suffix. Periodic
  recomputation and online adaptation are later questions.

Do not assume all 21 parameters are identifiable from the available grades
and intervals. Check excitation/coverage on training data; fix weakly
supported parameters or strengthen their priors rather than claim recovery
of an individual player's true parameter vector.

## Chronology, targets and state consistency

1. Split players into training, validation and final test groups. Derive
   history prefixes and later evaluation suffixes within each player.
2. Build every network input from its prefix only. No player-name embedding,
   archetype label, hidden C, original simulator weights, true recall or
   suffix aggregates may enter the predictor.
3. Given the generated weights, replay the prefix to initialize the state for
   the suffix. During suffix scoring, predict before consuming each outcome;
   already observed suffix outcomes may then update state for the next review.
4. Keep guided and short-delay events in state replay. For the first matched
   comparison, preserve the current eligible-review loss mask. Any later
   change to that mask is a separate, explicit comparison.
5. Use one declared elapsed-time convention across fitting, replay and scoring.
   Validate ordering and identity alignment rather than assume CSV row order.
6. Recompute state from history whenever the deployed parameter vector changes.
   A new vector cannot simply inherit stability/difficulty computed under old
   weights without an explicitly validated state-conversion method.

This proposal does not resolve the current per-move versus whole-line target
mismatch. The comparison must name its target and retain line-length strata;
a neural estimator of the same FSRS family cannot be assumed to remove that
structural limitation.

## Proposed comparison and resource limits

Purpose: exploratory investigation before a separately fixed confirmation.
No run has started and no compute budget has been agreed.

| Arm | What it tests |
|---|---|
| Current global binary fit | Existing population baseline |
| Current regularized personal fits | Whether the neural estimator adds value beyond ordinary personalization |
| Neural parameter estimator | Shared learning from history summaries |

First run the smallest matched comparison on a verified dataset, after the
baseline problems below are addressed. Proposed expansion: both existing
simulator families and five neural initialization seeds, with independently
generated population seeds where a generalization claim needs them. Repeating
initialization alone does not replicate the data-generating population.

Initial neural cap: 100 epochs with validation early stopping; initially one
32-unit hidden layer, no architecture search. Set the patience, CPU/GPU choice,
wall-time/RAM/disk budget and an adequate baseline optimization budget before
execution. Measure runtime; no speed claim is made. Stop or change approach
if replay parity fails, inputs leak future/hidden information, the agreed
resource cap is reached, or the data cannot distinguish the methods.

Select features, regularization, checkpoint and any fallback threshold on
training/validation players only. Compare final methods on the same unseen
players and eligible suffixes, including sparse-history fallbacks.
Fit the global baseline on training-player histories only. Fit each personal
baseline on that player's agreed prefix only, with the same cutoff and
fallback cohort as the neural arm. The current `personalise` helper creates
its own 60% split; do not reuse that implicit split if it differs from this
comparison's fixed prefixes.

Primary endpoint: paired held-out binary log-loss, with whole-player
resampling for uncertainty. Report both review-weighted and player-weighted
results, calibration, sparse/rich-history groups and line-length strata.
Report synthetic interval error separately; do not confuse it with reviews
saved. Decide the practical improvement and calibration tolerances before
confirmation; none are accepted here. Prediction gains do not establish
better human retention or lower review burden.

Retain source/input identities, feature schema, splits/cutoffs, seed values,
normalization, network checkpoint, generated parameter vectors, optimizer
outcomes, predictions, timing and raw results with the producing experiment.
The existing artifact and experiment-retention rules continue to apply.

## Runtime integration boundary

The current runtime loads a global weight file. Personal neural estimates
would additionally need player-to-model selection, parameter versioning,
history replay and global fallback. A network can run offline and export
ordinary FSRS vectors, but that does not make player-specific deployment a
drop-in file replacement. Keep research outputs separate from
`backend/fitted_global.csv`; rollout requires a separate decision and checks.

## Current approach: assessment and prerequisites

Assessment scope: source and retained artifacts at `62ff67b`, inspected on
2026-11-15. No optimization, generation or full ML suite was executed for this
assessment. Historical numerical results keep their original scope.

The basic approach is defensible: bounded maximum-likelihood fitting,
player-disjoint splits, validation-selected regularization, and replay of
guided events without treating them as recall tests. The question is whether
the model/target and comparison are appropriate, not whether L-BFGS-B is
inherently unsuitable. A separate read-only review reached the same conclusion.

### Findings, in priority order

The move/line distinction is now tracked separately as a
[possible bug](recall-target-mismatch.md), pending contract verification.
The user asked to leave the optimizer-start issue unchanged.

1. **Repair the comparison contract before attributing error to capacity.**
   The simulator uses one state per line, draws each move with the same R,
   and therefore produces whole-line clean probability R raised to the number
   of player moves. Hidden FSRS also adds a lapse floor; it is not an exact
   line-level FSRS recovery control. Sources:
   [session generation](../../ml/tempo_ml/simulator/clients.py),
   [hidden update](../../ml/tempo_ml/simulator/memory/fsrs.py) and the
   [implemented differences](../topics/synthetic-clients/record.md#8-simulator-app-and-accepted-specification).
   Inference: residual error combines representation mismatch, heterogeneity
   and optimization; it does not isolate neural-network headroom.
2. **There is direct evidence of an unfinished optimization baseline.**
   Historical A2 reports convergence at fit loss 0.560232, yet retained v1
   weights score 0.5532 on that same fit objective. Its test losses are 0.5620
   for A2 versus 0.5516 for v1. Thus a known feasible vector beats the fitted
   result; the data do not establish the best achievable FSRS fit. These are
   inspected historical numbers, not fresh measurements: see the
   [A2 raw log](../../ml/experiments/2026-11-13-fsrs-synthetic-v2/results/binary/train.log)
   and [v1 comparison](../../ml/experiments/2026-11-13-fsrs-synthetic-v2/SUMMARY.md#comparison-with-the-v1-weights-added-after-the-run).
   B2 and A1c also reach iteration limits. Recommend bounded alternative
   starts, including v1, with final selection on validation clients rather
   than test results. Historical test exposure means confirmation needs fresh
   held-out evidence.
3. **The large official-trainer deficit is sensitive to the clock.**
   Historical A1/A1c log-loss is 0.7135/0.6084 with exact-time replay, versus
   0.6127/0.6117 with calendar replay; the latter reported interval includes
   no difference. See the [recorded comparison](../../ml/experiments/2026-11-14-fsrs-memory/SUMMARY.md#results).
   Calendar scoring still uses the original exact-clock eligibility cohort.
   This supports a clock-sensitive comparison, not universal optimizer
   equivalence. Verify shared timestamps, masks, transitions and probability
   outputs against the actual runtime.
4. **Probability improvement is not scheduling benefit.**
   The historical [A2 interval results](../../ml/experiments/2026-11-13-fsrs-synthetic-v2/SUMMARY.md#results)
   retain worse long-interval errors despite improved log-loss. Data are
   collected by a separate fixed policy; app Learning initialization and
   grading also differ. Those are transfer questions before human realism.
   A closed-loop matched-policy study is a later decision, not evidence
   supplied by offline scoring or the proposed neural estimator.
5. **Sparse-history personalization has an implementation failure.**
   In [the trainer](../../ml/tempo_ml/fsrs/train.py), `personalise` returns an
   empty DataFrame with no columns when every player is skipped. Later,
   `main` accesses `late_log_loss_personal`, `late_log_loss_general` and
   `agent_name` unconditionally. With too little history, evaluation can also
   have an empty late mask. This prevents a dependable global fallback and
   must be handled before it is a neural-baseline comparator. Current binary
   CLI fitting additionally requires synthetic truth sidecars; it is not a
   complete human-data ingestion path.

The smallest research prerequisite is an exact line-level FSRS control with
shared timestamps, grades and state replay, followed by the bounded
default-start/v1-start comparison. Handle sparse cohorts explicitly. Keep the
neural model as an additional hypothesis rather than the explanation for
existing residual error.

### Executed sparse-history probe and limits

On 2026-11-15 a probe executed the current `time_split` and `personalise`
function definitions with the actual NumPy model and pandas, without invoking
an optimizer. One player with four eligible reviews produced zero late rows
and a DataFrame with no columns. Executing the trainer's subsequent
`agent_name` access raised `AttributeError: 'DataFrame' object has no attribute
'agent_name'`. The full CLI would access the other absent result columns
earlier; that complete CLI failure path was inspected, not executed.

Environment: bundled Python at
`C:/Users/thetr/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe`,
NumPy 2.3.5, pandas 3.0.1, model loaded from this checkout's
`ml/tempo_ml/fsrs/model.py`. SciPy, pytest and py-fsrs were unavailable there;
no dependency installation or full ML test run was performed. To reproduce
the helper probe from the repository root, run the following with that Python
interpreter (the extracted helpers do not enter `fit` for this sparse input):

```python
import ast, sys
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0, str(Path("ml").resolve()))
from tempo_ml.fsrs.model import Cards, predict, DEFAULT_PARAMETERS
from tempo_ml.evaluate.metrics import bce
path = Path("ml/tempo_ml/fsrs/train.py")
tree = ast.parse(path.read_text(encoding="utf-8"))
functions = [n for n in tree.body if isinstance(n, ast.FunctionDef)
             and n.name in {"time_split", "personalise"}]
scope = dict(np=np, pd=pd, Cards=Cards, predict=predict, bce=bce)
exec(compile(ast.Module(body=functions, type_ignores=[]), str(path), "exec"), scope)
cards = Cards(agent=np.array(["sparse"]), t=np.array([[0., 2., 3., 4., 5.]]),
    g=np.array([[3, 3, 1, 3, 3]]), valid=np.ones((1, 5), dtype=bool),
    y=np.array([[1., 1., 0., 1., 1.]]),
    loss_mask=np.array([[False, True, True, True, True]]),
    row=np.arange(5).reshape(1, 5))
_, _, late, per_agent = scope["personalise"](cards, DEFAULT_PARAMETERS, .1)
print(int(late.sum()), list(per_agent.columns))
per_agent["archetype"] = per_agent.agent_name.map({"sparse": "example"})
```

## Decisions still needed

- Goal: personal vectors, or one global vector? Recommend personal vectors
  for the neural proposal; otherwise compare direct gradient fitting first.
- Outcome model: continue whole-line FSRS as a baseline, or explicitly model
  line length/per-move recall? Recommend diagnosing this distinction before
  crediting any neural improvement to personalization.
- Experiment execution: agree the resource budget and practical success bars
  after the baseline audit. Implementation and runs wait on acceptance of
  the research direction; synthetic gains alone do not authorize deployment.
