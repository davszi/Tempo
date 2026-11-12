# Worklog

Append-only chronology, newest entries first. Keep detailed evidence in its producing experiment or topic.

## Bring the latest demo data into the frontend branch

On 2026-11-12, merged main at `dc4678d` into `feature/frontend`. The incoming tree changes add `demo/fitted_global.csv`, `demo/synthetic_reviews.csv` and `demo/tempo_demo.sqlite` without conflicts. Verified the staged demo files match main and that the merge changes no frontend files. Builds and backend runtime tests were not rerun because no source or dependency inputs changed; the demo data was imported unchanged. The merge commit supplies the source identity.

## Merge main into the frontend branch

On 2026-11-12, merged main at `4b2824d` into `feature/frontend` to bring the team's current backend, architecture documentation and GitHub Pages configuration into the frontend branch. Resolved the single conflict in `docs/index.md` by retaining the frontend route and all routes from main. The frontend TypeScript check and production build passed through `npm run build`. Backend runtime tests and documentation rendering were not rerun: their source was imported unchanged from main, and the manual resolution only combines documentation links. The merge commit supplies the source identity.

## TEMPO practice backend and presentation walkthrough

Added the practice controller, ML controller, FSRS runtime, and SQLite schema for Learning and Repeating. Added the offline synthetic review generator and a Windows launcher for the local demo. The documentation site now links the System Architecture and End-to-End Flow pages from the sidebar. Verified all four review grades using the supplied weights, persisted stability and due dates, and reproduced the 50,400-session synthetic CSV. The documentation build, freshness check, and lint passed. Generated site files and local demo data are Git-ignored. The landing commit supplies the source identity.

## Review dataset schema and human calibration topic record

Created the canonical topic record (`docs/topics/review-dataset/record.md`) and page source (`docs/topics/review-dataset/index.md`) defining the CSV review session schema (`agent_name, opening_name, review_status, t_days, grade, total_time_ms, accuracy`), the normalized 4-point FSRS grading function based on blunder status and cognitive delay ($\bar{\Delta}$), and the Stage 2 human telemetry calibration pipeline. Registered the topic in `docs/site/site.toml` and `docs/index.md`. No application code was implemented.

## Synthetic client cognitive and behavioral model topic record

Created the canonical topic record (`docs/topics/synthetic-clients/record.md`) and page source (`docs/topics/synthetic-clients/index.md`) defining the cognitive traits, log-normal hesitation sampling, practice-based automaticity decay, FSRS retrievability, and soft blunder penalties for simulated players. Registered the topic in `docs/site/site.toml` and `docs/index.md`. No application code was implemented.

## Shared TEMPO context in the project context

Merged the team's shared TEMPO background (product purpose, vocabulary, the two modes, review planner, FSRS, synthetic clients, the four parts in scope, the earlier prototype and agent guidelines) into `docs/PROJECT_CONTEXT.md`, replacing the starter's placeholder purpose line. Reason: `AGENTS.md` makes that file the one orientation every agent reads first, and the kit names it the canonical home for project purpose, so a separate context file would go unread or duplicate it. The starter's repository map, build and review sections are kept unchanged. Only the Repeating Mode behaviour and synthetic training data are recorded as decided; everything under "What we are building now" stays open for team discussion. No build or application behaviour was measured. The commit hash is assigned by this entry's landing commit.

## Starter origin

Created a neutral documentation example with a project-owned page registry, a shared build-sheet theme and a visual guide. No application behavior or benchmark was measured. No consumer build or browser result is claimed by this template. The repository commit containing this file supplies its initial source identity.
