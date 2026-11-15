# Product backlog and acceptance gaps

This record owns the six product requests previously detailed in
`docs/open/OPEN.md`. Status comes from source inspection on 2026-11-15 of
local merge `5d6b81c`, not a new integrated app test. The [frontend](../frontend/frontend.md),
[opening catalog](../opening-catalog/opening-catalog.md) and
[FSRS training](../fsrs-training/fsrs-training.md) records own current behavior
and evidence. Implementation does not supersede accepted product decisions.

| Request | Implemented or recorded | Remaining acceptance |
|---|---|---|
| Days until forgetting | Browser due labels, recall, stability and unreviewed/overdue states | Agree on wording and shared engine/demo calculation |
| Explain benchmarks | Dated runs contain baselines, splits, parameters, commands and metrics | Accessible interpretation, persona/seed limits and honest generalization |
| Improvements in days | Threshold-error metrics exist | Compare review burden and forgetting outcomes per persona on matched workloads |
| Review schedule | Selectable 30-day dashboard timeline and overdue grouping | Integrated database/timezone and empty-state checks |
| Repertoire access | Permanent navigation, search, side/status filters, moves and history | Complete acceptance and resolve direct-review policy |
| Clean opening data | App catalog cleaned to 2,719 lines | Reconcile reproducible import with removal of the old classifier |

## 1. Days until forgetting

The original request requires a meaningful estimate per learned line, tests
for unreviewed/overdue/today cases, and the same calculation in UI and demo.
`frontend/src/lib/memory.ts` labels the scheduled review date using
`next_review_at`. The backend also returns recall and stability.
`backend/demo.py` prints stability and the next timestamp, not that relative
day label. A due date is a schedule, not proof of exactly when recall crosses
90%: learning/relearning steps and scheduler options matter.

Unresolved choice: time until scheduled review, or a separate curve-derived
threshold estimate such as 50% recall. Recommend scheduled-review wording
until another threshold is agreed. Do not promise a person will forget on
that date. The choice gates changed calculation and full demo acceptance.

## 2. Benchmark interpretation

The previous assertion that no benchmarks exist is obsolete. The
[pass/fail versus true-recall run](../../../ml/experiments/2026-11-13-fsrs-synthetic-v2/SUMMARY.md)
and [FSRS-memory run](../../../ml/experiments/2026-11-14-fsrs-memory/SUMMARY.md)
retain synthetic results and reproduction inputs. Acceptance requires that
readers can distinguish log-loss, calibration, error against hidden truth,
and schedule error; identify baseline/oracle and held-out players; and see
effects and limitations across personas. Per-player benefit, human realism
and generalization over random seeds are not established by one global fit.
No experiment was rerun in this audit.

## 3. Practical scheduling benefit

Days-to-threshold error does not count reviews saved. The original request
also compares strong/weak-line intervals, reviews over a fixed horizon,
Again rate, and too-early/too-late reviews. It needs matched baseline and
fitted policies, per-persona results and worked examples. Longer intervals
are beneficial only without increased forgetting. This broader comparison
remains open; agree on protocol and acceptance before running it.

## 4. Review schedule

`frontend/src/components/DashboardPage.tsx` implements the 30-day schedule;
`frontend/src/lib/memory.ts` groups due dates and overdue lines. Selecting a
day lists its lines; repertoire detail has history. Acceptance includes
agreement with stored UTC timestamps and local calendar days, empty state,
and overdue/today cases. Helper tests do not establish HTTP/database/browser
agreement. Prior browser checks remain dated evidence in the worklog.

## 5. Repertoire access

`frontend/src/components/Shell.tsx` provides permanent access.
`RepertoirePage.tsx` shows learned lines and in-progress lessons with search,
side/status controls, moves, recall and history. The full unlearned catalog
is browsed separately in Learning. Check whether that separation meets the
original request to expose available lines beside repertoire status.

The backlog requested starting a selected review, but that contradicts the
settled planner-only Repeating rule in [project context](../../PROJECT_CONTEXT.md#4-the-two-modes).
The implementation already offers it. The [frontend record](../frontend/frontend.md)
owns the unresolved choice; this backlog does not authorize that deviation.

## 6. Opening data and reproducibility

Cleaning means removing three full White moves or fewer, not three
half-moves. The [opening-catalog record](../opening-catalog/opening-catalog.md)
owns the cleaned catalog and later regrouping. The old classifier, TSV and
derived CSV under `ml/ml_1000bots/openings/` were removed at `ea3d01d`;
they remain retrievable at `825e9d8`.

`ml/tempo_ml/catalog.py` reads the SQLite catalog, not the removed TSV.
A future import must identify source, cleaning rule, stable line identities
and hashes, and protect player history. The [opening-library record](../opening-library/opening-library.md)
owns the historical evidence and remaining reproducibility choice. This audit
does not change the catalog or saved user data.
