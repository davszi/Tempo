# Agent entrypoint

Read `docs/PROJECT_CONTEXT.md` once for orientation, unless already loaded.
Use `docs/index.md` for named documentation routes. Initialize the pinned
`.docs-kit` submodule before relying on its rules. If required shared policy is
missing, report it and resolve the prerequisite before proceeding with the
work it governs.

## Read before the relevant action

Apply every matching route before its action. Load additional routes when
scope expands. Follow named topic and experiment links for task-specific
inputs. These routes grant no execution or publication permission.

| Before… | Read… |
|---|---|
| Changing source, tests or repository configuration | `.docs-kit/rules/engineering/code.md` and the owning project topic or development guide |
| Changing runtime cost or making performance claims | `.docs-kit/rules/engineering/performance.md` and the project's workload/acceptance contract |
| Designing or running an experiment, qualification or benchmark | `.docs-kit/rules/experiments/workflow.md` and the project's owning experiment records |
| Choosing or changing experiment checks or interpreting their failures | `.docs-kit/rules/experiments/verification.md` and the project's accepted verification contract |
| Running tests, builds, benchmarks or other expensive jobs | `.docs-kit/rules/engineering/execution.md` and the project's recorded environment and execution requirements |
| Assigning work, coordinating contributors or editing in parallel | `.docs-kit/rules/engineering/delivery.md` |
| Reporting completion or blockers, handing off work or integrating a handoff | `.docs-kit/rules/engineering/handoffs.md` |
| Staging, committing or rewriting Git history | `.docs-kit/rules/engineering/git.md` and the project's recorded validation requirements |
| Changing anything under `.docs-kit/` or moving its pin | **The shared kit submodule** in `.docs-kit/rules/engineering/git.md` |
| Upgrading the kit pin or taking over the repository | The new version's migration guide, `.docs-kit/docs/topics/releases/migrations/<version>.md`, then `.docs-kit/rules/conformance.md` |
| Writing or changing a record: a guide, topic record, plan, worklog or open-work entry | `.docs-kit/rules/records.md`, and in `.docs-kit/rules/documentation.md` the sections from **Record first, page on request** through **Rules for changes and chronology** |
| Creating, moving, splitting or retiring a document | `.docs-kit/rules/documentation.md` |
| Making a new page for people, only when a person asked for one, or page work on an existing page beyond a small sync | **Record first, page on request** and **Rendered pages are for people** in `.docs-kit/rules/documentation.md`; the page author reads the applicable focused guides linked from `.docs-kit/rules/writing.md` and `.docs-kit/rules/maintenance.md` |
| Building, checking, reviewing rendered output, publishing or changing the site | The applicable focused guides linked from `.docs-kit/rules/maintenance.md` and **Build and review** in `docs/PROJECT_CONTEXT.md` |
