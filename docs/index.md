# Documentation reading index

[Project context](PROJECT_CONTEXT.md) owns TEMPO's purpose, vocabulary and
settled decisions, the repository map, build commands
and project choices. [Task routes](../AGENTS.md) name the guides to read before
each action.

## Current documentation

- [Frontend dashboard](topics/frontend/frontend.md): scope, design source, component ownership and validation.
- [TEMPO end-to-end flow](topics/whole-flow/whole-flow.md) connects the catalog, practice, scheduling, and offline data.
- [TEMPO database schema](topics/database-schema/database-schema.md) describes opening lines, practice events, and player progress.
- [Opening catalog structure](topics/opening-catalog/opening-catalog.md): why opening families and lines are stored as they are, family sides, the line tree and which lines can be learned.
- [TEMPO system architecture](topics/system-architecture/system-architecture.md) covers component data flow, practice modes, and review scheduling.
- [Starter topic record](topics/guide/guide.md): architecture, ownership and adoption acceptance.
- [Visual guide source](topics/guide/index.md): the registered human-facing authoring example.
- [Synthetic clients topic record](topics/synthetic-clients/record.md): specification for cognitive traits, latency and familiarity simulation.
- [Synthetic clients page source](topics/synthetic-clients/index.md): visual explanation of synthetic client simulation.
- [Review dataset topic record](topics/review-dataset/record.md): specification for review session CSV schema, FSRS grading function, and human calibration.
- [Review dataset page source](topics/review-dataset/index.md): visual explanation of session telemetry, grading decision tree, and calibration pipeline.
- [FSRS training on synthetic clients](topics/fsrs-training/fsrs-training.md): the implemented simulator `ml/ml_1000bots/`, dataset tempo_v1, FSRS-6 training method, results and proposals.
- [Retraining plan for the cleaned catalog](topics/fsrs-training/retraining-plan.md): retrain both FSRS-6 variants, add true-recall experiment arms and an error metric in days, and remove datasets from the variant folders.
- [Opening library](topics/opening-library/opening-library.md): real Lichess lines used by the simulator, their classification and White/Black side with evidence from real games.
- [First training run, 2026-11-11](../ml/ml_1000bots/runs/2026-11-11-first-training/SUMMARY.md): experiment record with parameters, reproduction commands, environment, attempts and raw outputs.
- [Home source](topics/home/index.md): the optional project-owned landing page.
- [Open work](open/OPEN.md): routes to unfinished owners.
- [Worklog](worklog.md): append-only chronology.

## Shared practices

Read the matching guide in the initialized `.docs-kit` submodule:

| Action | Shared guide |
|---|---|
| Code, performance or execution | `rules/engineering/code.md`, `performance.md`, `execution.md` |
| Delivery, handoffs or Git | `rules/engineering/delivery.md`, `handoffs.md`, `git.md` |
| Writing or changing a record | `rules/records.md` |
| Documentation placement, order of work and lifecycle | `rules/documentation.md` |
| A page for people: new on request, existing kept in step | Focused guides linked from `rules/writing.md` and `rules/maintenance.md` |
| Site authoring, checks, publication and reader changes | Focused guides linked from `rules/maintenance.md` |

Add named links here when project-owned development guidance, evidence or
session records are needed. Follow the shared canonical-home rules; create no
empty record collections or duplicate status boards.
