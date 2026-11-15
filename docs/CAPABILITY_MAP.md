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

No new supporting-tool need was approved by this documentation audit. Future
needs and the owner's decisions belong here under the shared guide.
