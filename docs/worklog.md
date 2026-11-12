# Worklog

Append-only chronology, newest entries first. Keep detailed evidence in its producing experiment or topic.

## Review dataset schema and human calibration topic record

Created the canonical topic record (`docs/topics/review-dataset/record.md`) and page source (`docs/topics/review-dataset/index.md`) defining the CSV review session schema (`agent_name, opening_name, review_status, t_days, grade, total_time_ms, accuracy`), the normalized 4-point FSRS grading function based on blunder status and cognitive delay ($\bar{\Delta}$), and the Stage 2 human telemetry calibration pipeline. Registered the topic in `docs/site/site.toml` and `docs/index.md`. No application code was implemented.

## Synthetic client cognitive and behavioral model topic record

Created the canonical topic record (`docs/topics/synthetic-clients/record.md`) and page source (`docs/topics/synthetic-clients/index.md`) defining the cognitive traits, log-normal hesitation sampling, practice-based automaticity decay, FSRS retrievability, and soft blunder penalties for simulated players. Registered the topic in `docs/site/site.toml` and `docs/index.md`. No application code was implemented.

## Shared TEMPO context in the project context

Merged the team's shared TEMPO background (product purpose, vocabulary, the two modes, review planner, FSRS, synthetic clients, the four parts in scope, the earlier prototype and agent guidelines) into `docs/PROJECT_CONTEXT.md`, replacing the starter's placeholder purpose line. Reason: `AGENTS.md` makes that file the one orientation every agent reads first, and the kit names it the canonical home for project purpose, so a separate context file would go unread or duplicate it. The starter's repository map, build and review sections are kept unchanged. Only the Repeating Mode behaviour and synthetic training data are recorded as decided; everything under "What we are building now" stays open for team discussion. No build or application behaviour was measured. The commit hash is assigned by this entry's landing commit.

## Starter origin

Created a neutral documentation example with a project-owned page registry, a shared build-sheet theme and a visual guide. No application behavior or benchmark was measured. No consumer build or browser result is claimed by this template. The repository commit containing this file supplies its initial source identity.
