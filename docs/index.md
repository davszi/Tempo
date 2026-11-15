# Documentation reading index

[Project context](PROJECT_CONTEXT.md) owns TEMPO's purpose, settled decisions,
repository map and commands. [Task routes](../AGENTS.md) name the shared guides
to read before an action. The main menu is a reading path; Reference contains
all eligible tracked Markdown records, plans and results.

## Reading order

| Order | Overview | Question it answers |
|---|---|---|
| 1 | [App & practice](https://davszi.github.io/Tempo/html/whole-flow.html) | What does the player do, and what is saved? |
| 2 | [System architecture](https://davszi.github.io/Tempo/html/system-architecture.html) | Which components serve the app, and where does offline fitting stop? |
| 3 | [Catalog & data](https://davszi.github.io/Tempo/html/opening-catalog.html) | Where do lines come from, which can be learned, and how is practice stored? |
| 4 | [Synthetic players](https://davszi.github.io/Tempo/html/synthetic-clients.html) | How are recall, retries and latency simulated? |
| 5 | [Review data & grading](https://davszi.github.io/Tempo/html/review-dataset.html) | What does a session export mean, and how is its grade assigned? |
| 6 | [FSRS training](https://davszi.github.io/Tempo/html/fsrs-training.html) | How are parameters fitted and evaluated, and what do the results establish? |

## Topic boundaries and canonical records

- **App & practice** combines the human journey with the browser overview.
  [Whole flow](topics/whole-flow/whole-flow.md) owns the cross-topic walkthrough;
  [frontend application](topics/frontend/frontend.md) owns screens, API, storage
  and unresolved Repeating behavior. It does not duplicate architecture detail.
- **System architecture** owns component and deployment boundaries, runtime
  scheduling and offline fitting. Its [record](topics/system-architecture/system-architecture.md)
  is the technical owner; practical demo commands are routed from the journey.
- **Catalog & data** is one reader-facing overview of three distinct owners:
  [catalog rules](topics/opening-catalog/opening-catalog.md), [database fields](topics/database-schema/database-schema.md)
  and [historical opening provenance](topics/opening-library/opening-library.md).
  Those records remain separate so historical tooling is not mistaken for the
  current catalog or schema.
- **Synthetic players** explains the producer model. The [record](topics/synthetic-clients/record.md)
  owns traits, memory, recall and latency assumptions.
- **Review data & grading** explains the output interface and grade policy.
  Its [record](topics/review-dataset/record.md) distinguishes implemented telemetry
  from future human calibration; calibration is a chapter, not a separate
  implemented subsystem.
- **FSRS training** explains fitting and evaluation. The [record](topics/fsrs-training/fsrs-training.md)
  owns current method and scoped conclusions; the simulator equations stay in
  the synthetic-player topic rather than being repeated as another overview.

## Supporting Reference material

- [Product backlog](topics/product/product.md) and [open work](open/OPEN.md):
  remaining acceptance and unresolved choices, not an extra mechanism topic.
- [ML setup](../ml/README.md), the [retained retraining plan](topics/fsrs-training/retraining-plan.md),
  and experiment records below support the training overview. The plan is not
  retired by this navigation cleanup.
- [Pass/fail versus true recall, 2026-11-13](../ml/experiments/2026-11-13-fsrs-synthetic-v2/SUMMARY.md)
  and [FSRS-memory clients, 2026-11-14](../ml/experiments/2026-11-14-fsrs-memory/SUMMARY.md):
  separate historical runs, with their input identities, results and caveats.
- [Capability map](CAPABILITY_MAP.md): supporting-tooling inventory and new needs.
- [Worklog](worklog.md): completed work and dated verification.

Every canonical record above has an automatic Reference HTML counterpart.
Overview sources are the corresponding topic `index.md` files; the combined
catalog/data overview lives in `topics/opening-catalog/index.md`. Reference
routes derive from file paths, so this presentation pass preserves the records'
paths and historical experiment identities.

## Shared practices

Read the matching guide in the initialized `.docs-kit` submodule:

| Action | Shared guide |
|---|---|
| Code, performance or execution | `rules/engineering/code.md`, `performance.md`, `execution.md` |
| Delivery, handoffs or Git | `rules/engineering/delivery.md`, `handoffs.md`, `git.md` |
| Writing or changing a record | `rules/records.md` |
| Documentation placement, order of work and lifecycle | `rules/documentation.md` |
| Pages and explanations | Focused guides linked from `rules/writing.md` |
| Site authoring, checks and publication | Focused guides linked from `rules/maintenance.md` |
