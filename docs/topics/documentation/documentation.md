# Documentation adoption and audit

## Scope and source

This record owns Tempo's kit adoption, documentation audit, verification and
remaining choices. The audit starts from local merge `5d6b81c` on 2026-11-15:
all project docs, six existing topic pages, site configuration, app source
and current ML code. Historical experiment records/results and old worklog
entries retain their original source scope.

Work is limited to docs and their configuration. It does not change app
behavior, catalog, inputs or weights. Checks cover documentation build, lint,
reader regression and rendered review; no training or benchmark is rerun.
A contradiction requiring a product decision is recorded, not resolved by
inventing approval. Temporary failed checks are distinguished from results.

## Kit and environment

| Item | Identity |
|---|---|
| Previous kit | 3.2.1, `f34cf63e769fa49a16e42f9768aa239e94dadac5` |
| Adopted kit | 5.0.0, `25c058d094160faa517ec16f72ab44ed984c87ad` |
| Migration | 4.0 content steps, then 5.0; one pin movement |
| Environment | `.build/docs-env`, created using desktop-bundled Python; project-local dependencies |
| Packages | `mistune==3.3.4`, `Pygments==2.21.0` |
| Python | 3.12.14; the plain `python` alias on this host did not work, so the project environment was created from the bundled interpreter |
| Build output | `.build/docs/`, ignored |
| Commands | [Project context](../../PROJECT_CONTEXT.md#documentation-website) |

The initial 3.2.1 build passed. Strict lint found 29 pre-existing `OPEN.md`
bullets without owning-document links. The first 5.0 build passed; its strict
lint also found numbers only on the Guide slide face. These baseline
findings do not establish an app regression.

## Publication scope

`reference_listing = false` preserves the six existing pages and their
routes: Home, Guide, Synthetic Clients, Review Dataset, System Architecture
and End-to-End Flow. Other topics remain Markdown. No page lock or new
publication workflow is enabled. Kit 5 can list tracked Markdown as Reference
pages automatically; that broader scope is deferred pending review of exact
candidates and exclusions. A local build or commit does not authorize push
or deployment.

## Audit corrections

- Current app records distinguish implemented browser/API behavior from
  proposed hosted deployment and future personalized planning.
- Storage/API descriptions separate browser identity/progress from SQLite
  history and identify the absence of account authentication.
- The settled no-hints/planner-selected Repeating contract remains; current
  deviations are recorded for a decision in the frontend topic.
- ML docs distinguish current `ml/tempo_ml/` commands from retired simulators
  and historical results. Source pins and measured limitations remain.
- Product acceptance has a subject record; `OPEN.md` holds routes instead
  of detailed, partly stale checklists.
- The router includes the new capability-map route. No dedicated reusable
  supporting-tooling tree is declared; domain app/ML source and experiment
  scripts keep their existing owners.
- Manifest-hashed SVG figures use LF checkout through `.gitattributes`, so
  Windows line-ending conversion does not silently change their byte identity.

A read-only SQLite query in the documentation environment confirmed 2,719
lines, 82 families (43 White, 39 Black), 1,889 learnable terminal variations,
and a minimum of four White moves. The connection used `mode=ro`; no startup
migration or practice session ran. The source remains `backend/tempo_demo.sqlite`.

Input identity: `5d6b81c:backend/tempo_demo.sqlite`, Git blob
`f955e4d5a141d8ff9d34fa66831a8f57c4d39613`, SHA-256
`5eb848f110d5f3634344b854038a4482a16c7d2ecc7da782b01c2b326188eaa0`.
Reproduce with the documentation interpreter from the project root:

```python
import sqlite3
db = sqlite3.connect('file:backend/tempo_demo.sqlite?mode=ro', uri=True)
lines = db.execute('SELECT moves_uci FROM opening_lines').fetchall()
print(len(lines))
print(db.execute('SELECT COUNT(*) FROM opening_families').fetchone()[0])
print(db.execute('SELECT family_side, COUNT(*) FROM opening_families GROUP BY family_side').fetchall())
print(min((len(row[0].split()) + 1) // 2 for row in lines))
print(db.execute('SELECT COUNT(*) FROM opening_lines o WHERE NOT EXISTS '
                 '(SELECT 1 FROM opening_lines p WHERE p.parent_line_id=o.line_id)').fetchone()[0])
db.close()
```

### Historical evidence gaps

The FSRS-memory experiment record's exploratory percentages and optimizer
observations at `ml/experiments/2026-11-14-fsrs-memory/SUMMARY.md` describe
uncommitted exploratory code/output that was not retained. Those observations
are not independently reproducible from the retained artifacts. Its opener
also says only hidden memory differed, while its own inputs/caveat show the
catalog regrouped from 91 to 82 families. The current training topic explains
that confound; the historical record is not rewritten by this pass.

Git identifies that experiment's indirect 'landing commit' source as
`ea3d01d7743dac5f513d853e1ef5c0d451e3b105`. A new claim based on the missing
exploratory artifacts needs a retained rerun; this audit does not manufacture
evidence or authorize that experiment. The full current experiment tables
remain distinct from the unretained exploratory observations.

## Conformance and verification

Executed after integration: full site build, freshness check, strict lint,
and `build --check-reader` pass; the latter preserves words, links, media,
anchors and SVG geometry for all five reader pages. The home page uses no
chapter reader. All 47 formulas on three pages compile with KaTeX 0.16.11.
Source inspection is not app runtime or visual validation.

A disposable fresh local clone of the committed candidate also passed the
full build, freshness, strict lint, five-page reader check and all 47 formula
compilations. Its submodule was initialized at the exact adopted pin; only
tracked project sources were available. The figure SHA-256 still matched
after Windows checkout. This reused the documented pinned documentation
environment; it is not a clean-machine dependency-install qualification.

Shared-engine checks were also executed with the generated starter fixture:
347 Python tests ran in 177.083 seconds, with 9 failures, 4 errors and 28
skips. The suite is not clean on this Windows host. Reported cases include
POSIX `/tmp` working directories, slash-format expectations, CRLF byte
comparisons, path ordering and Windows path normalization in pin/local-file
checks. The pin helper compares Git's slash-form path with a native Path;
the consumer's actual pin was therefore additionally checked with
`git -C .docs-kit branch -r --contains HEAD`, which lists `origin/main`.
No shared-kit source or test expectations were changed to hide these failures.

The failing modules/cases were `test_kit_pin` (two unpublished-pin checks),
`test_portability` (three unrelated-working-directory errors and two shared
asset byte comparisons), `test_markers` (registry path extraction),
`test_reference_listing` (route ordering), `test_site_contract` (declared
local artifact path), `test_source_links` and two `test_source_pages` cases
(slash-form link diagnostics). No rerun with altered thresholds or patched
upstream code was used. Missing optional page-lock dependencies account for
some skips; the suite's exact skip reasons remain its own test output.

The Node reader-navigation/fold/key/dialog/history/column tests and
panel-switcher logic tests pass. Math-renderer and source-file-link Node
tests pass after supplying the generated starter output at their expected
fixture path; their first invocation lacked that fixture. These fake-DOM
checks are not browser pixel inspection. Page-lock behavior was not adopted
or qualified. The passing Tempo checks do not imply the entire upstream
cross-platform suite passes.

| Conformance item | Disposition |
|---|---|
| Pin | v5.0.0 release reachable on kit remote |
| Build/lint/freshness/reader | Pass in working checkout and fresh tracked clone; 47 formulas compile; shared-suite Windows failures reported separately |
| Router | New capability-map route added; existing routes retained |
| Shared rules | Shared guides remain in kit; records contain project facts |
| Canonical homes | Context/index/topics/worklog/open routes present |
| Tooling | `tooling_roots = []`; capability map states current scope |
| Topic structure | Six existing sources; no new public topic page |
| Records/pages | Content reconciled; face design decision below |
| Open work | One-line linked routes |
| Compatibility | Existing topic routes and standalone HTML retained |
| Changed guides | Existing Guide/Home updated for kit and project |
| Rendered review | Six pages at wide/phone widths; all eight faces in-page and deck; paired diagrams checked; limits below |

## Rendered review

The page author reviewed the six published pages at 1440 by 1000 and 390 by
844, and the coordinator inspected the captures by eye. No document-level
horizontal overflow or broken images were observed. Latency/calibration
figures were also checked in two equal 495-pixel columns: their steps stack,
and long formulas scroll inside their own region. Phone chapter navigation
opens, Escape closes it and returns focus, Tab exposes a visible layout-control
outline, and deck Left/Right navigation works. These are focused checks, not
exhaustive accessibility or touch qualification.

Two observed rendering faults were fixed: shared CSS had overridden the
architecture SVG's region colors, and kit image inlining dropped the image's
minimum width. Original selector specificity and an opaque dark canvas now
preserve contrast; an inner labelled scroll region keeps the 970 by 422
drawing at 900 pixels wide on a phone. Its 12-pixel source labels therefore
render at approximately 11.13 pixels (design scale arithmetic). The source
HTML, definition and manifest recipe remain together, and extraction was
verified byte-identical to the SVG and its recorded SHA-256. LF checkout keeps
that identity stable across hosts.

All eight faces were inspected in their page and extracted deck at both
widths. No text cut off or parts outside the face were observed. Wide deck
faces are 1440 by 810; phone faces stack. Each still needs an owner decision
about design under the new real-visual rule:

| Face | First focus and empty-band observation | Design finding |
|---|---|---|
| `guide#pipeline` | Title, then highlighted ownership tile; broad bands above/below tiles | Tiles name owners but omit the chapter's flow arrows |
| `guide#slides` | Title, then bright 1/0 counts; broad bands around factor list | Text factors/counts repeat the chapter rather than show its mechanism |
| `system-architecture#components` | Host takeaway title, then application-host tile; broad bands around row | Deployment boxes lack the real component drawing shown below |
| `system-architecture#practice` | Shared-history title, then Learning/Repeating pair; broad bands | Labels do not show the actual state/grade transition |
| `system-architecture#live-demo` | Outcome title, then Run tile; broad bands | Run/read/inspect list is textual rather than a visual result |
| `whole-flow#catalog` | Catalog title, then catalog count tile; broad bands | Counts and labels do not show catalog structure |
| `whole-flow#learning-to-schedule` | Practice-flow title, then Learn tile; broad bands | Three labels repeat the prose without its transitions |
| `whole-flow#present-and-inspect` | Saved-review title, then PowerShell tile; broad bands | Text-only task list does not show the saved record |

The compact phone faces remain legible. The faces were not redesigned,
removed or newly created. Review-only generated decks/captures are scratch;
the observations above are the durable result.

Not executed: rendered no-JavaScript fallback, browser reduced-motion mode,
print output, exhaustive keyboard/touch checks, the shared automated browser
helper, or app runtime tests. Node tests cover some reader print/motion logic
in an imitation DOM; that does not qualify the browser output. The retained
standalone database-schema HTML received a content/source synchronization,
not a separate rendered qualification.

## Unresolved choices

### Reference publication

Options: retain six-page scope, enable automatic references with reviewed
exclusions, or register selected records. Recommend selected records only
after reviewing content/routes. No migration step is blocked because the
current scope is preserved.

### Requiring formula checks on every host

The local strict lint run compiles formulas with Node and the kit's KaTeX.
`formula_check_required` remains unset, so a host without Node can skip that
check with a note. Options: require it and explicitly provision Node wherever
lint runs, or retain the kit default. Recommend requiring it for CI after the
owner agrees to that dependency. The migration's owner decision is still open;
local formula success is not a claim that every host enforces it.

### Finished retraining plan

`docs/topics/fsrs-training/retraining-plan.md` says its work is completed or
superseded. Kit 4/5 asks to retire finished working documents after lasting
content has a current home and concrete deletion approval. Its accepted
days metric, recovery criteria and diagnostic-weight restriction must be
accounted for first. Recommend that coverage check followed by approved
retirement. The plan is retained pending that decision.

### Secondary README and legacy HTML

`ml/README.md` is a useful setup guide but kit 5 expects one root README.
Recommend approving a rename to `ml/ML_GUIDE.md`, updating current links and
preserving historical source identities. It remains in place pending approval.

The standalone `database-schema.html` and `system-architecture.html` in
their topic folders duplicate records/generated pages. This audit corrects
them and retains their routes. Options: retire them after checking consumers,
or retain an explicit synchronization duty. Recommend retirement only after
the owner confirms outside use and the exact paths.

### Existing slide design

Existing faces are retained. Kit 5 asks for a real visual per face; boxes
that repeat lead text may need redraw/removal. The rendered review names the
affected chapters and any observed layout faults. Recommend a separate
approved face-design pass; lint alone does not establish design quality.
