+++
toc = []
title = "FSRS training"
slug = "fsrs-training"
description = "Follow fitting, evaluation and the limits of the recorded synthetic-memory experiments."
brand_sub = "offline fitting · synthetic evidence · runtime boundary"
components = ["toc", "nav", "code", "filelinks"]
page_css = ["build-sheet.css"]
math = true
+++

# FSRS training

<section class="card" id="offline-and-runtime">

## Training studies memory; the app schedules practice

<p class="bs-lead">Offline fitting improved prediction on the recorded synthetic populations; it has not established better retention for human players.</p>

<figure id="fig-training-boundary">
<div class="bs-grid g2" role="img" aria-label="Separate lanes: offline simulated histories train and evaluate weights, with hidden truth available only for diagnostics. The app stores real practice events and uses its runtime Scheduler to choose a due line; the diagnostic weights are not deployed.">
<div class="bs-part bs-violet"><h3>Offline study</h3><p><strong>Opening catalog → synthetic players → session histories</strong></p><p>Fit weights from grades and elapsed time. Hidden recall truth provides a diagnostic target and evaluation reference.</p><p><strong>Held-out players → prediction metrics</strong></p></div>
<div class="bs-part bs-teal"><h3>App runtime</h3><p><strong>Practice events → stored card state → FSRS Scheduler</strong></p><p>The runtime chooses the oldest due line. It currently loads the older first-fit global weights, not these diagnostic weights.</p><p><strong>Due line → the next Repeating session</strong></p></div>
</div>

<figcaption><strong>Figure 1.</strong> Source-authored lanes from the <a href="docs.topics.fsrs-training.fsrs-training.md.html#simulator-app-and-accepted-specification">offline/runtime comparison</a> and <a href="docs.topics.fsrs-training.fsrs-training.md.html#earlier-1000-client-simulator-removed">runtime weight provenance</a>. Arrows mean data or scheduling flow; the lanes do not imply automatic model deployment.</figcaption>
</figure>

[Figure 1](#fig-training-boundary) separates a research result from a shipping decision. The app's `backend/fitted_global.csv` comes from an older global fit on 800 synthetic clients. Which synthetic weights the demo should load remains an open choice; none of these studies validates weights for real players.

The package and app also differ in Learning initialization, review intervals, retry handling and eligible lines. Those [implemented differences](docs.topics.fsrs-training.fsrs-training.md.html#simulator-app-and-accepted-specification) limit transfer even before human realism is considered.

</section>

<section class="card" id="method">

## Hold players out before fitting the memory model

<p class="bs-lead">Each study compares training targets on the same histories within that study, then evaluates on players excluded from fitting.</p>

<figure id="fig-fit-flow">
<div class="bs-flow" role="img" aria-label="Generate synthetic histories, separate fitting and evaluation players, fit FSRS weights, then score held-out histories. True recall enters diagnostic arms only.">
<div class="bs-node bs-violet"><span class="bs-label">Generate</span><b>Simulated histories</b><p>Catalog, client traits and a chosen hidden memory model.</p></div>
<div class="bs-arrow"><span>split</span></div>
<div class="bs-node bs-orange"><span class="bs-label">Fit</span><b>FSRS weights</b><p>Pass/fail targets or diagnostic hidden truth; evaluate neither on fitting players.</p></div>
<div class="bs-arrow"><span>score</span></div>
<div class="bs-node bs-teal"><span class="bs-label">Evaluate</span><b>Unseen players</b><p>Prediction, calibration and days-to-threshold errors.</p></div>
</div>

<figcaption><strong>Figure 2.</strong> Source-authored fitting flow from the dated <a href="ml.experiments.2026-11-13-fsrs-synthetic-v2.summary.md.html#protocol-from-the-plan-fixed-before-the-run">multiplicative-memory protocol</a> and <a href="ml.experiments.2026-11-14-fsrs-memory.summary.md.html#protocol">FSRS-memory protocol</a>.</figcaption>
</figure>

[Figure 2](#fig-fit-flow) shows why the split is by player: the reported test histories do not train the shared weights. Each dated study uses 60 test clients and a further 60 new hold-out clients. The [synthetic-player model](synthetic-clients.html) generates attempts; [review data and grading](review-dataset.html) defines the observable session summaries.

<div class="scroll" role="region" aria-label="Training methods; scroll horizontally on narrow screens" tabindex="0" data-reader-horizontal style="overflow-x:auto">
<div style="min-width:560px">

| Study and arm | Trainer | Fitting target |
|---|---|---|
| Multiplicative memory · A2 | Shared package trainer | Observed session pass/fail; log-loss |
| Multiplicative memory · B2 | Shared package trainer | Hidden clean-session probability; mean squared error |
| FSRS memory · A1 | py-fsrs Optimizer | Observed ratings/pass-fail history |
| FSRS memory · A1c | Shared package trainer | Observed session pass/fail; log-loss |
| FSRS memory · B1 | Shared package trainer | Hidden clean-session probability; mean squared error |


</div>
</div>

The B arms are diagnostic: real players supply outcomes, not a known probability of recall. They do not define candidate app inputs. Both hidden models retain line-level state and independently sample moves, so a clean line's probability is $R^M$, where $R$ is per-move recall and $M$ the player's move count. This is not exact recovery of an unmodified FSRS process.

</section>

<section class="card" id="metrics">

## Probability error and scheduling error answer different questions

<p class="bs-lead">A model can improve recall prediction while still choosing a poor time to revisit long-lived memories.</p>

<div class="scroll" role="region" aria-label="Metric definitions; scroll horizontally on narrow screens" tabindex="0" data-reader-horizontal style="overflow-x:auto">
<div style="min-width:600px">

| Instrument | What it asks | Reading the result |
|---|---|---|
| Log-loss | Does the probability agree with observed pass/fail? | Lower is better; confident wrong predictions cost more. |
| Calibration RMSE, binned | Among similar predicted probabilities, how often did reviews pass? | Lower is better; reported in percentage points. |
| RMSE against hidden truth | How far is prediction from the simulator's known clean-session chance? | Lower is better; a synthetic-only reference unavailable for real players. |
| Days-to-threshold error | When does the predicted chance reach the threshold, relative to hidden truth? | Predicted minus true days: negative is early; positive is late. |


</div>
</div>

The [accepted days metric](docs.topics.fsrs-training.retraining-plan.md.html#days-metric) uses a 90% clean-session threshold. It measures a curve crossing, not reviews saved or a promise about when a person forgets. The population's overall median can hide much larger errors among long-lived lines; the result sections therefore include that limitation beside the headline scores.

These studies do not count the practical benefit of an alternative policy. Review burden and forgetting outcomes on matched workloads remain [unfinished product acceptance](docs.topics.product.product.md.html#3-practical-scheduling-benefit).

</section>

<section class="card" id="multiplicative-results">

## Multiplicative-memory fitting reduced synthetic prediction error

<p class="bs-lead">In the November 13 study, pass/fail fitting captured most of the improvement available from the diagnostic true-chance target.</p>

<div class="scroll" role="region" aria-label="Multiplicative-memory prediction results; scroll horizontally on narrow screens" tabindex="0" data-reader-horizontal style="overflow-x:auto">
<div style="min-width:560px">

| Predictor | Test log-loss | Calibration RMSE | RMSE against truth |
|---|---:|---:|---:|
| FSRS-6 defaults | 0.723 | 19.2 pp | 27.7 pp |
| A2 · pass/fail | 0.562 | 2.6 pp | 14.1 pp |
| B2 · hidden truth | 0.560 | 2.1 pp | 13.8 pp |


</div>
</div>

Historical synthetic test results from [November 13, 2026](ml.experiments.2026-11-13-fsrs-synthetic-v2.summary.md.html#results). The complete record includes constant baselines, held-out results, per-profile errors and fitted weights.

<div class="scroll" role="region" aria-label="Multiplicative-memory scheduling errors; scroll horizontally on narrow screens" tabindex="0" data-reader-horizontal style="overflow-x:auto">
<div style="min-width:560px">

| Predictor | Overall median days error | Median error for true intervals of at least 30 days |
|---|---:|---:|
| FSRS-6 defaults | +0.00 d | −38.6 d |
| A2 · pass/fail | −0.14 d | −47.0 d |
| B2 · hidden truth | −0.10 d | −45.0 d |


</div>
</div>

The [days tables](ml.experiments.2026-11-13-fsrs-synthetic-v2.summary.md.html#results) show why the overall median is insufficient: both trained models call the long-lived lines substantially early. B2 reached the 300-iteration limit without convergence. This is one recorded fit, not evidence that its target or optimizer has reached the best solution.

</section>

<section class="card" id="fsrs-memory-results">

## Clock conventions changed the FSRS-memory comparison

<p class="bs-lead">In the November 14 study, matching the elapsed-time convention removed the apparent advantage over the py-fsrs trainer.</p>

<div class="scroll" role="region" aria-label="FSRS-memory prediction results; scroll horizontally on narrow screens" tabindex="0" data-reader-horizontal style="overflow-x:auto">
<div style="min-width:520px">

| Predictor | Exact-clock test log-loss | RMSE against hidden truth |
|---|---:|---:|
| FSRS-6 defaults | 0.8307 | 32.5 pp |
| A1 · py-fsrs | 0.7135 | 24.7 pp |
| A1c · shared trainer | 0.6084 | 12.2 pp |
| B1 · hidden truth | 0.6091 | 12.3 pp |


</div>
</div>

Historical synthetic test results from [November 14, 2026](ml.experiments.2026-11-14-fsrs-memory.summary.md.html#results). A1's trainer uses calendar days. On that clock, test log-loss was 0.6127 for A1 and 0.6117 for A1c; the reported uncertainty interval includes no difference. The result does not establish a trainer advantage on the calendar-day clock.

Training on hidden truth added no benefit over A1c in this run. A1c reached the 300-iteration limit, and the [full results](ml.experiments.2026-11-14-fsrs-memory.results.tables.md.html) retain the other clock, hold-out clients and days errors.

The November 13 and 14 experiments used different catalog groupings: 91 and 82 families. Their scores are separate within-run comparisons, not a controlled comparison changing hidden memory alone. Some earlier exploratory observations also lack retained producing artifacts; the [historical evidence limits](docs.topics.fsrs-training.fsrs-training.md.html#historical-evidence-gaps) distinguish them from the retained experiment tables.

</section>

<section class="card" id="reproduction-and-limits">

## Reproduce a dated study from its recorded inputs

<p class="bs-lead">Today's configuration and catalog can generate new data; exact historical reproduction also needs the recorded code state and input identities.</p>

<div class="scroll" role="region" aria-label="Study reproduction links; scroll horizontally on narrow screens" tabindex="0" data-reader-horizontal style="overflow-x:auto">
<div style="min-width:440px">

| Need | Start here |
|---|---|
| Install the current package and run it | [ML setup and reproducibility](ml.readme.md.html) |
| Reproduce the multiplicative-memory study | [Recorded source, inputs and commands](ml.experiments.2026-11-13-fsrs-synthetic-v2.summary.md.html#reproduce) |
| Reproduce the FSRS-memory study | [Recorded reproduction instructions](ml.experiments.2026-11-14-fsrs-memory.summary.md.html#reproduction) |
| Inspect accepted metric and recovery criteria | [Retained retraining plan](docs.topics.fsrs-training.retraining-plan.md.html#decisions) |
| Understand what still needs agreement | [Current method and limits](docs.topics.fsrs-training.fsrs-training.md.html#limits) and [product acceptance gaps](docs.topics.product.product.md.html) |


</div>
</div>

No human calibration, multi-seed generalization or measured improvement in human retention is established here. The current simulator also has an unresolved retry-cap outcome. Keep those limits attached to the results when using them to choose the next investigation.

</section>
