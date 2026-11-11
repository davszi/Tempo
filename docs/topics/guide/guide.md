# Authoring example: source, evidence and reader

## Scope

This topic owns the starter's illustrative documentation architecture and acceptance checklist. It makes no claim about application behavior, benchmark results or completed browser checks. The human-facing explanation is `index.md`.

## Ownership

| Item | Canonical owner |
|---|---|
| Project orientation and commands | `docs/PROJECT_CONTEXT.md` |
| Site title, source repository/ref and navigation | `docs/site/site.toml` |
| Shared rules, reader and theme | Pinned `.docs-kit` submodule |
| Subject facts and future accepted requirements | The relevant named topic record |
| Human explanation | Topic `index.md`, drawn from its record |
| Raw experiment evidence | Producing experiment directory |
| Unfinished work routing | `docs/open/OPEN.md` |
| Chronology | `docs/worklog.md` |

## Diagram sources

The numbered HTML flows on the guide are authored directly in `index.md`. They depict ownership and information direction; they contain no measured quantities. Their page source is their generator. Changes require wide/narrow rendered inspection and reference/anchor checks. No remote media or fonts are required.

## Acceptance checklist

- Initialize a version-pinned shared-kit submodule and configure the real source repository/ref.
- Register every published page; keep links and public anchors stable.
- Build, check freshness and lint from the project root.
- Inspect wide, narrow and two-column reading, keyboard/focus, reduced motion, print and no-JavaScript fallback.
- Keep each measured claim linked to source revision, inputs, runtime, command, units and results.
- Rerun before applying a result to changed measured inputs or behavior.
- State checks as passed only after they have actually run.

## Example verdict

The starter demonstrates the shared-kit architecture selected for this package. Alternatives in the human page compare ownership and maintenance costs rather than measured timing. A project adopting the starter still owns its integration and review checks.
