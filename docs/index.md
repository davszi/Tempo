# Documentation reading index

[Project context](PROJECT_CONTEXT.md) owns TEMPO's purpose, vocabulary and
settled decisions, the repository map, build commands
and project choices. [Task routes](../AGENTS.md) name the guides to read before
each action.

## Current documentation

- [TEMPO end-to-end flow](topics/whole-flow/whole-flow.md) connects the catalog, practice, scheduling, and offline data.
- [TEMPO database schema](topics/database-schema/database-schema.md) describes opening lines, practice events, and player progress.
- [TEMPO system architecture](topics/system-architecture/system-architecture.md) covers component data flow, practice modes, and review scheduling.
- [Starter topic record](topics/guide/guide.md): architecture, ownership and adoption acceptance.
- [Visual guide source](topics/guide/index.md): the registered human-facing authoring example.
- [Synthetic clients topic record](topics/synthetic-clients/record.md): specification for cognitive traits, latency and familiarity simulation.
- [Synthetic clients page source](topics/synthetic-clients/index.md): visual explanation of synthetic client simulation.
- [Review dataset topic record](topics/review-dataset/record.md): specification for review session CSV schema, FSRS grading function, and human calibration.
- [Review dataset page source](topics/review-dataset/index.md): visual explanation of session telemetry, grading decision tree, and calibration pipeline.
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
