# Possible bug: move recall versus whole-line recall

Status: open, suspected model/target mismatch; not a confirmed implementation
defect. The user requested tracking this possibility on 2026-11-15. No change
to simulation, fitting or runtime behavior has been approved.

## What is verified

Source inspected at `62ff67b`:

- `SyntheticClient.review` in
  [session generation](../../ml/tempo_ml/simulator/clients.py) computes one
  retrievability R from the line's memory state, then draws every player move
  with that same success probability. Any first-attempt mistake fails the
  clean-session outcome. Under these independent draws, whole-line success
  probability is R raised to the number of player moves.
- `load_cards` in [the fitting model](../../ml/tempo_ml/fsrs/model.py) makes
  one card per player/line and uses `grade > 1` as the whole-session success
  label. Its FSRS prediction is therefore fitted to whole-line success.
- [Evaluation](../../ml/tempo_ml/evaluate/metrics.py) compares that prediction
  to whole-session labels and hidden `p_clean`. It does not accidentally
  score against per-move R. The possible mismatch concerns the modeled
  process and its interpretation, rather than a demonstrated wrong label.

## Why this might be a bug

If the intended contract says the simulator and fitter share the same
meaning of FSRS recall, or that the FSRS-memory study is an exact parameter
recovery control, the implementation does not meet that expectation:
per-move probability and whole-line probability differ whenever a line has
multiple player moves and recall is between zero and one.

However, deliberately fitting a line-level FSRS approximation to whole-line
outcomes can be valid. FSRS may absorb some differences through its fitted
parameters and states. The observed distinction alone does not prove the
binary target is incorrect or quantify its effect on scheduling.

Inference: residual prediction error and line-length effects cannot yet be
attributed solely to insufficient FSRS capacity or optimization. Generating
memory with FSRS does not by itself make the whole-session target an exact
FSRS recovery test. Hidden lapse-floor changes and player heterogeneity are
additional differences; isolate them rather than blame everything on length.

## Investigation and closure

1. Establish the intended meaning of recall: an individual move, or completing
   the whole line cleanly. Check the generator, training labels, displayed
   probabilities and retention/interval targets against that same meaning.
2. Use a minimal exact line-level FSRS control with identical timestamps,
   grades and state updates. Then introduce the existing per-move draws and
   varying line lengths separately. No experiment has been run for this item;
   agree its bounded execution budget before starting.
3. If an unintended mismatch is demonstrated, propose the smallest correction
   and corresponding acceptance checks. If the approximation is intentional,
   document it and narrow any exact-recovery claims. Either outcome can close
   the suspected bug once its evidence and decision are recorded.

Unresolved choice: retain whole-line FSRS as an intentional approximation,
explicitly include line length/per-move behavior in the observation model,
or change the generator to whole-line recall for the recovery control.
Recommendation: establish the contract and control first; do not choose an
architecture change from this observation alone. Implementation waits on
that decision.

Related context: [existing simulator/app differences](../topics/synthetic-clients/record.md#8-simulator-app-and-accepted-specification)
and [neural-weight proposal](neural-fsrs-weights.md#current-approach-assessment-and-prerequisites).
The separate optimizer-start issue is left unchanged, as requested.
