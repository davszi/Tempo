# Authoring example: source, evidence and reader

## Scope

This topic owns Tempo's documentation authoring example, ownership map and
acceptance checklist. The human-facing explanation is `index.md`; it illustrates
the shared kit, not the chess application's runtime architecture or measured
performance. [Project context](../../PROJECT_CONTEXT.md#documentation-website)
owns current setup; [the worklog](../../worklog.md#2026-11-15-relocate-the-kit-audit)
records completed checks and their limits.

Tempo pins kit 5.0.0. The site's six topic pages are Home, Guide, Synthetic
Clients, Review Dataset, System Architecture and End-to-End Flow. Records in
other folders remain Markdown. The project explicitly sets
`reference_listing = false`, so the upgrade does not publish every tracked
Markdown file automatically. Existing topic and public anchor identities are
preserved. Publication remains a separate action after local verification.

The guide's slide example explains the shared reader: below 720 px the face
uses the kit's compact layout; each chapter has at most 1 opening face, and a
chapter with nothing to show needs 0 faces. These are authoring constraints,
not measurements of application performance. The view menu provides
Presentation options, and All chapters shows faces only when Slides is enabled.

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

The guide demonstrates the shared-kit architecture selected for Tempo.
Alternatives compare ownership and maintenance costs rather than measured
timing. The [worklog](../../worklog.md#2026-11-15-relocate-the-kit-audit) states
the checks actually executed. Publication choices stay in
[project context](../../PROJECT_CONTEXT.md#documentation-publication-choices),
and slide design choices stay in this record. The checklist does not
establish that every check has passed.

## Slide design review

The existing faces `guide#pipeline` and `guide#slides` remain in place. The
[2026-11-15 rendered review](../../worklog.md#2026-11-15-relocate-the-kit-audit) records their
title-first emphasis, broad empty bands and text-heavy layouts. Kit 5
asks for a real visual per face. Options: redraw the faces, remove
those with nothing visual to add, or explicitly retain them as a
temporary exception. Recommend a separate approved design pass.
Redrawing or removing these faces waits on that decision; passing lint
does not establish design conformance.
