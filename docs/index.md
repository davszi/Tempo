# Documentation reading index

[Project context](PROJECT_CONTEXT.md) owns purpose, accepted decisions,
repository orientation and run/build commands. [Task routes](../AGENTS.md)
identify the adopted shared guides. The seven real topics below each have a
canonical record and a requested explanatory HTML entry page. Reference
renders supporting records, setup, open work and dated experiment material.

## Reading order

| Order | Topic and HTML page | Canonical record and responsibility |
|---|---|---|
| 1 | [App & practice](https://davszi.github.io/Tempo/html/whole-flow.html) | [App & Practice](topics/app-practice/app-practice.md): player journey, screens, board input, identity, saved lessons, HTTP contract and display semantics |
| 2 | [System architecture](https://davszi.github.io/Tempo/html/system-architecture.html) | [System Architecture](topics/system-architecture/system-architecture.md): components, process/session/transaction boundaries, due-line selection, runtime FSRS and demo |
| 3 | [Catalog & data](https://davszi.github.io/Tempo/html/opening-catalog.html) | [Catalog & Data](topics/catalog-data/catalog-data.md): line identity, catalog decisions, all four tables, store operations, constraints and migration |
| 4 | [Synthetic players](https://davszi.github.io/Tempo/html/synthetic-clients.html) | [Synthetic Players](topics/synthetic-clients/record.md): traits, memory models, recall/retry/timing/session generation and separate demo producer |
| 5 | [Review data & grading](https://davszi.github.io/Tempo/html/review-dataset.html) | [Review Dataset](topics/review-dataset/record.md): observable export, grading inputs, the earlier grade rule, hidden-truth boundary and future human calibration |
| 6 | [Session grading](https://davszi.github.io/Tempo/html/session-grading.html) | [Session Grading](topics/session-grading/session-grading.md): the decided grading rule (mistake limits, time bands), its rationale, test vectors, implementation targets, open items and validation plan |
| 7 | [FSRS training](https://davszi.github.io/Tempo/html/fsrs-training.html) | [FSRS Training](topics/fsrs-training/fsrs-training.md): fitting inputs/objectives, optimizer, evaluation/clock/metric contracts, artifacts, dated results and limits |

## Actual merges and splits

Frontend and the whole-flow record are merged into `app-practice`; there are
no separate frontend or whole-flow topic folders. Architecture links to the
app journey instead of maintaining a second walkthrough. Runtime scheduling
belongs to Architecture; offline fitting belongs to Training.

Catalog decisions and database field mappings are merged into `catalog-data`.
[Historical opening-library provenance](topics/catalog-data/provenance.md)
is supporting evidence in that same topic, with its retired classifier and
dated input identities preserved. A historical preparation path does not
establish a current importer.

Simulator implementation and hidden memory models belong to Synthetic
Players. Training links to that producer and owns fitting/evaluation instead.
Review Data & Grading remains one output contract; its human-calibration
specification is marked future. The decided grading rule has its own topic,
Session Grading, because its implementation spans the simulator, training
and the app; Review Data keeps the export's grading inputs and the earlier
synthetic evidence. Historical study protocols and results remain
with their producing experiments. The completed retraining plan's durable
requirements are incorporated into Training; its superseded task text remains
available through its pinned Git reference there.

A topic's `index.md` explains its canonical record for people. Full field and
endpoint lookup, source coverage tables, exact provenance and run chronology
stay in linked Reference pages. Source coverage is explicitly scoped source
inspection; a successful HTML build is not a completeness or app-acceptance test.

## Supporting material

- [Product backlog](open/product-backlog.md) owns unfinished acceptance;
  [Open work](open/OPEN.md) routes unresolved questions to their owners.
- [ML setup and reproducibility](development/ml.md) owns package installation,
  CLI commands and configuration/artifact use.
- [Multiplicative-memory study](../ml/experiments/2026-11-13-fsrs-synthetic-v2/SUMMARY.md)
  and [FSRS-memory study](../ml/experiments/2026-11-14-fsrs-memory/SUMMARY.md)
  retain their separate historical inputs, protocols, results and reproduction.
- [Move recall model](topics/move-recall/move-recall.md) owns the decision
  that FSRS recall means one player move, the 0.9 pass-chance scheduling
  target and the training arms; [training approaches](topics/move-recall/approaches.md)
  describes the accuracy and pass-chance targets. Decided 2026-11-16, not
  implemented; no page yet.
- [Capability map](CAPABILITY_MAP.md) identifies supporting tooling.
- [Worklog](worklog.md) records dated changes and verification, including the
  code-to-documentation audit's scope and limits.

## Shared practices

Read the matching guide in the initialized `.docs-kit` submodule:

| Action | Shared guide |
|---|---|
| Code, performance or execution | `rules/engineering/code.md`, `performance.md`, `execution.md` |
| Delivery, handoffs or Git | `rules/engineering/delivery.md`, `handoffs.md`, `git.md` |
| Records and canonical ownership | `rules/records.md`, `rules/documentation.md` |
| Human pages and figures | Focused guides linked from `rules/writing.md` |
| Site build, browser checks and publication | Focused guides linked from `rules/maintenance.md` |

`AGENTS.md` is the rule router. `PROJECT_CONTEXT.md` is the project orientation.
Neither duplicates the shared kit's policy.
