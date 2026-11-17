# Capability map

`docs/site/site.toml` declares `tooling_roots = []`. Source inspection on
2026-11-15 found no dedicated reusable supporting-tooling tree: `backend/`
and `frontend/` implement the app, `ml/tempo_ml/` implements the domain's
simulator/trainer/evaluation, and scripts under dated experiment folders serve
their own runs. The shared documentation tools are supplied by `.docs-kit`.

Read [Name the need first](../.docs-kit/rules/engineering/code.md#name-the-need-first)
before adding supporting tooling. This inventory is not authorization to build
a new harness or move existing domain source.

## Capabilities

| Need | Code | State | Imported by |
|---|---|---|---|

## Seen but not built

| Need | Seen | Decision |
|---|---|---|
| Run a batch of jobs on the university Slurm cluster and collect their output | 2026-11-16, [move-recall experiment](../ml/experiments/2026-11-16-move-recall/PLAN.md) | 2026-11-16, the person: build the minimum inside the experiment (`run.sbatch`); no shared tool |
