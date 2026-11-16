+++
toc = []
title = "Review data and grading"
slug = "review-dataset"
description = "Read the session export and correctness-first grade policy, with human calibration kept as future work."
brand_sub = "session telemetry · FSRS grading · human calibration"
components = ["toc", "nav", "code", "filelinks"]
page_css = ["build-sheet.css"]
math = true
+++

# Review data and grading

<section class="card" id="schema">

<span id="review-dataset-schema--human-calibration-pipeline"></span>

## Session summaries expose outcomes while hidden memory stays separate

<p class="bs-lead">The package exports session summaries with recall accuracy, summed attempt latency and an FSRS grade; move events and hidden memory stay separate.</p>

The [dataset record](docs.topics.review-dataset.record.md.html#2-review-session-dataset-schema) defines this CSV interface. The rows below are illustrative, including the human example; they are not evidence of collected human telemetry.

```csv
agent_name,opening_name,review_status,t_days,grade,total_time_ms,accuracy
synth_blitzer_01,Ruy Lopez: Berlin Defense,review,2.4,3,3420,1.0
synth_diligent_02,Sicilian Defense: Najdorf,relearning,0.5,1,8940,0.75
human_tester_01,French Defense: Winawer,review,5.1,4,1980,1.0
```

### Column Specification:
- **`agent_name`:** Unique identifier for synthetic client or human tester.
- **`opening_name`:** The specific opening variation tested.
- **`review_status`:** `new` (first seen), `learning` (assisted with arrows), `review` (unassisted test), or `relearning` (post-lapse recovery).
- **`t_days`:** Days elapsed since previous review of this opening line.
- **`grade`:** Standard FSRS 4-point rating (`1: Again`, `2: Hard`, `3: Good`, `4: Easy`).
- **`total_time_ms`:** Sum of all attempt latencies, including retries and physical baseline; it is not an independently measured session wall-clock duration.
- **`accuracy`:** First-attempt accuracy ratio across the line ($1.0$ for clean runs).

Opening names are unique within each simulated client's sampled repertoire, which lets the trainer use `(agent_name, opening_name)` as its card key. Names are not globally unique; a human-data export still needs a line-identity decision. The backend uses `line_id`. Hidden values such as stability and $p_{\mathrm{clean}}$ belong to `ground_truth.csv`, outside this telemetry schema.

Guided `new` and `learning` sessions have perfect accuracy and receive latency-based grades. They update model state but do not contribute to training loss. The same loss exclusion applies to unassisted rows with `t_days < 1`. Excluded rows are replayed, rather than deleted or treated as failed recall; the <a href="fsrs-training.html#state-replay">training explanation</a> shows the mask and state boundary.

<p>Generate each independently identified dataset into a fresh directory. Reusing a previous FSRS directory can leave stale hidden-weight CSVs that the new manifest still hashes; the <a href="docs.topics.review-dataset.record.md.html#5-generated-files-and-producer-boundaries">record</a> explains this source-derived limit. Historical contamination has not been established.</p>

</section>


<section class="card" id="generated-files">

## Keep observable sessions aligned with their hidden diagnostic sidecars

<p class="bs-lead">The package exports more than its session CSV; hidden truth supports evaluation without becoming observable player telemetry.</p>

<figure id="fig-output-alignment">
<div class="bs-flow">
<div class="bs-node"><b>One simulated session</b><small>In-memory move outcomes determine the summary and hidden memory state.</small></div>
<div class="bs-arrow"><span>write</span></div>
<div class="bs-stack"><div class="bs-part"><h3>sessions.csv</h3><p>Observable status, elapsed time, grade, summed latency and accuracy.</p></div><div class="bs-part"><h3>ground_truth.csv</h3><p>Matching row position with hidden recall chance, stability and familiarity.</p></div></div>
<div class="bs-arrow"><span>align</span></div>
<div class="bs-node"><b>Replay & score</b><small>Card replay retains the original row index to align predictions with truth. It does not validate sidecar identities for you.</small></div>
</div>
<figcaption><strong>Figure 1.</strong> Arrows mean export and positional alignment, not a join on a globally unique opening name. Generator: this page's HTML; input: <a href="docs.topics.review-dataset.record.md.html#5-generated-files-and-producer-boundaries">generated-file contract</a> and <a href="docs.topics.fsrs-training.fsrs-training.md.html#evaluation-metrics">scoring alignment</a>.</figcaption>
</figure>

<a href="#fig-output-alignment">Figure 1</a> explains why reordering a sidecar independently can invalidate a score even when the files still parse. The scorer aligns by CSV row position, rather than joining or checking hashes. Preserve the alignment and verify the generator manifest for independently supplied inputs.

<div class="scroll" role="region" aria-label="Observable and hidden dataset outputs; scroll horizontally on narrow screens" tabindex="0" data-reader-horizontal style="overflow-x:auto">
<div style="min-width:700px">

| Output | Role | Available from ordinary human telemetry? |
|---|---|---|
| <code style="white-space:nowrap">sessions.csv</code> | Observable session summaries; one guided or unassisted session per row. | A future export could supply comparable outcomes, but its stable line identity and collection contract are not agreed. |
| <code style="white-space:nowrap">ground_truth.csv</code> | Row-aligned hidden per-move recall, clean chance, stability/familiarity and session context. | No; these are simulator state. |
| <code style="white-space:nowrap">clients.csv</code>, <code style="white-space:nowrap">repertoires.csv</code> | Synthetic traits, attendance/budget and selected line IDs/move counts. | Not fitted human traits or an implemented human export. |
| <code style="white-space:nowrap">memory_weights.csv</code> | Per-client hidden weights written for FSRS-memory runs; use a fresh output directory when changing models. | No; these are hidden generating parameters, not fitted runtime weights. |
| <code style="white-space:nowrap">manifest.json</code> | Config/model, counts, catalog identity, output hashes, producing source and environment. | Reproduction evidence, rather than practice telemetry. |

</div>
</div>


Generation does not delete pre-existing hidden-weight files when switching to multiplicative memory, and the manifest hashes every CSV already in the output directory. Reusing an older directory can therefore retain and hash stale or unrelated files. This follows source control flow; it does not show that a retained historical run was contaminated. Use a fresh output directory for an independently identified dataset.

The producer rounds exported elapsed time, probabilities, stability and integer-millisecond latency. It grades from the underlying attempt sum before rounding. Individual move events stay in memory: the session CSV cannot recover move order, individual attempt latency or whether the final capped retry succeeded. Move count and physical baseline are needed for grading but are absent from its seven fields. The <a href="docs.topics.review-dataset.record.md.html#5-generated-files-and-producer-boundaries">full output mapping</a> gives exact fields and precision.

The backend demo uses the same header with different move counting, retry and schedule rules, and no package sidecars/manifest. App requests persist move events in SQLite; the inspected code establishes no completed app-to-training exporter. See <a href="synthetic-clients.html#collection-policy">producer comparison</a> for these different histories.

</section>

<section class="card" id="grading">

## Correctness decides failure before the mean time per move decides a clean grade

<p class="bs-lead">Any first-attempt error gives Again. A clean session is graded only by its mean time per move, the one timing the app can measure for a real player. The intervals that split it into Easy, Good and Hard are still being established.</p>

<figure id="fig-grading">
<div class="bs-grid g2" role="img" aria-label="Any first-attempt error gives Again. For a clean session, the mean time per move is compared with two intervals that are still to be established: fast gives Easy, normal gives Good, slow gives Hard.">
<div class="bs-part bs-orange"><h3>Any first-attempt error?</h3><p><strong>Yes → 1 · Again</strong></p><p>Retry time does not turn a failed first attempt into clean recall.</p></div>
<div class="bs-part bs-teal"><h3>No → mean time per move</h3><p><strong>Fast → 4 · Easy</strong></p><p><strong>Normal → 3 · Good</strong></p><p><strong>Slow → 2 · Hard</strong></p><p>The boundaries between fast, normal and slow are open.</p></div>
</div>
<figcaption><strong>Figure 2.</strong> Source-authored branches of the <a href="docs.topics.review-dataset.record.md.html#32-decision-logic">session grading rule</a> decided on 2026-11-16. No interval values are shown because none has been set.</figcaption>
</figure>

[Figure 2](#fig-grading) puts correctness first. Time distinguishes grades only after every first attempt is correct. For a clean session the rule divides the total time by the number of repertoire moves $M$:

$$\bar{T} = \frac{\text{total\_time\_ms}}{M}$$

| Condition | Grade |
|---|---|
| Any first-attempt error | 1 — Again |
| Clean; mean time per move below the Easy boundary | 4 — Easy |
| Clean; mean time per move between the two boundaries | 3 — Good |
| Clean; mean time per move above the Hard boundary | 2 — Hard |

**Why no baseline any more.** The earlier rule subtracted each player's physical move time (`baseline_ms`) and graded only the hesitation that remained, against fixed thresholds. Both are removed: the app cannot know a real player's baseline, so the simulated players and the app now grade by the same measurable quantity. A player's physical speed is part of the time that is graded.

**Not implemented yet.** The simulator and the app keep the earlier rule until the intervals are set, so every recorded synthetic dataset and result was graded with it. The [grading record](docs.topics.review-dataset.record.md.html#3-the-session-grading-function) tracks that status.

### Where the time per move comes from

<figure id="fig-hesitation-grade">
<div class="bs-flow" role="img" aria-label="Each simulated move takes the player's physical baseline plus a hesitation that weak recall lengthens and practice shortens. The mean over the line's moves is the time that is graded.">
<div class="bs-node bs-violet"><span class="bs-label">Each move</span><b>Baseline + hesitation</b><p>Physical move time plus a random hesitation, longer when recall is weak, shorter with practice.</p></div>
<div class="bs-arrow"><span>average over M</span></div>
<div class="bs-node bs-orange"><span class="bs-label">Clean session</span><b>Mean time per move</b><p>Thinking and the physical move together.</p></div>
<div class="bs-arrow"><span>intervals</span></div>
<div class="bs-node bs-teal"><span class="bs-label">Grade</span><b>Easy, Good or Hard</b><p>Boundaries still to be established.</p></div>
</div>
<figcaption><strong>Figure 3.</strong> Source-authored path from the <a href="docs.topics.review-dataset.record.md.html#33-where-the-time-per-move-comes-from-synthetic-clients">simulated move times to the mean time per move</a>. Arrows show computation in the synthetic clients, not measured human timing.</figcaption>
</figure>

In a clean session each simulated move is right on its first attempt, so it has exactly one time: the player's baseline plus a hesitation. The mean time per move is

$$\bar{T} = \text{baseline\_ms} + \frac{1}{M}\sum_{i=1}^{M} 1000\,H_i\,e^{\beta(1-R)}\frac{1}{1+\alpha\,\text{reps}}, \qquad H_i\sim\operatorname{Lognormal}(\mu,\sigma)$$

- **Physical speed counts.** The baseline is added to every move, so a faster-handed player gets faster grades.
- **Weak memory slows the player.** Lower recall $R$ raises the time through $e^{\beta(1-R)}$, most for high-effort players (large $\beta$).
- **Practice speeds the player up.** Each clean session adds one to reps and a blunder removes two; the hesitation is divided by $1+\alpha\cdot\text{reps}$.
- **Speed and luck.** $\mu$ sets the player's typical pace, and each session draws new hesitations; averaging $M$ moves steadies longer lines. A blunder gives Again whatever the time.

<div class="scroll" role="region" aria-label="Expected mean time per move by profile; scroll horizontally on narrow screens" tabindex="0" data-reader-horizontal style="overflow-x:auto">
<div style="min-width:620px">

| Profile | Fresh line (R = 1) | R = 0.9 | R = 0.7 | R = 0.7 after 5 clean sessions |
|---|---|---|---|---|
| Blitzer | 827 ms | 852 ms | 905 ms | 469 ms |
| Balanced | 1187 ms | 1280 ms | 1497 ms | 832 ms |
| Diligent | 1815 ms | 2168 ms | 3157 ms | 1768 ms |

</div>
</div>

The table is formula arithmetic at each profile's mean traits: the expected mean time per move, not a measurement. Real simulated clients spread around these traits and draw new hesitations every session. With FSRS hidden memory the grade also changes how fast the line's memory grows; with multiplicative memory it does not ([hidden memory models](synthetic-clients.html#hidden-memory)).

### What the simulated players actually use

Every bot gets its own traits: a random draw around its profile's average, with the spread below, limited to the allowed range. The last three columns are the real lowest and highest values among the 300 bots of the November 13 multiplicative-memory run.

<div class="scroll" role="region" aria-label="Trait values of the simulated players; scroll horizontally on narrow screens" tabindex="0" data-reader-horizontal style="overflow-x:auto">
<div style="min-width:900px">

| Trait | What it does | Average: Blitzer / Balanced / Diligent | Spread (sd) | Allowed | Blitzer bots | Balanced bots | Diligent bots |
|---|---|---|---|---|---|---|---|
| `baseline_ms` | Physical move time added to every move | 220 / 300 / 380 ms | 25 ms | 150–500 ms | 151–277 ms | 240–355 ms | 303–467 ms |
| $\mu$ | Typical hesitation $e^\mu$ seconds: 549 / 819 / 1350 ms at the averages | −0.6 / −0.2 / 0.3 | 0.15 | any | −0.97 to −0.13 | −0.53 to 0.11 | −0.16 to 0.69 |
| $\sigma$ | How much single hesitations vary | 0.45 / 0.40 / 0.35 | 0.05 | > 0 | 0.33–0.54 | 0.27–0.52 | 0.22–0.49 |
| $\beta$ | Effort: slowdown when recall is weak | 0.4 / 1.0 / 2.2 | 0.2 | ≥ 0 | 0–0.86 | 0.50–1.44 | 1.66–2.60 |
| $\alpha$ | Speed-up per practice repetition | 0.35 / 0.25 / 0.20 | 0.04 | 0.1–0.5 | 0.25–0.46 | 0.18–0.37 | 0.10–0.30 |
| $C$ | Forgetting power | 0.65 / 0.50 / 0.35 | 0.05 | > 0 | 0.54–0.80 | 0.38–0.66 | 0.25–0.49 |

</div>
</div>

Only three bots touched a limit: one at the lowest practice rate and two with zero effort. Under the new rule the baseline is part of the graded time, as it already is for real players in the web app ([System Architecture](system-architecture.html#practice)).

### Establishing the intervals

The intervals are open work. A first synthetic check regraded the 76,287 clean reviews of the November 13 run:

<div class="scroll" role="region" aria-label="Grade shares under the earlier rule and a candidate; scroll horizontally on narrow screens" tabindex="0" data-reader-horizontal style="overflow-x:auto">
<div style="min-width:640px">

| Rule | Easy | Good | Hard |
|---|---|---|---|
| Earlier rule, as recorded in the data | 31.5% | 65.1% | 3.4% |
| Mean time per move, earlier boundaries kept | 5.8% | 85.5% | 8.7% |
| Mean time per move, candidate 800 / 2100 ms | 35.3% | 60.6% | 4.1% |

</div>
</div>

Kept unchanged, the earlier boundaries would make Easy rare, because they were set for hesitation without the physical move. The candidate raises both by 300 ms, about the bots' median baseline (302 ms); it keeps the overall mix close to the earlier one and changes 6.5% of clean grades. This only relates the candidate to the earlier rule; where human recall really changes needs mean times per move from real players in the app. The [evidence section](docs.topics.review-dataset.record.md.html#35-evidence-for-choosing-the-intervals) gives the per-profile shares.

The [synthetic-client explanation](synthetic-clients.html#memory-dynamics) shows why longer lines have a lower clean-session probability under independent recall draws. The app's separate backend grading path is explained in [System Architecture](system-architecture.html#practice).

</section>

<section class="card" id="calibration">

## Human calibration needs evidence and agreed acceptance criteria

<p class="bs-lead">Human calibration is a future specification; the package currently supplies trait-sampling hooks, without a fitted human cohort or validation result.</p>

[Figure 4](#fig-calibration) shows the specified calibration direction. Every stage awaits implementation and human evidence; the arrows do not describe an executed pipeline.

<figure id="fig-calibration">
<div class="bs-flow" role="img" aria-label="Future human calibration: collect human move telemetry, estimate latency and memory traits, then fit cohorts for synthetic trait sampling. No stage has a human-fit result.">
<div class="bs-node bs-violet"><span class="bs-label">Future input</span><b>Human telemetry</b><p>Move times, first-attempt errors and review history</p></div>
<div class="bs-arrow"><span>estimate</span></div>
<div class="bs-node bs-orange"><span class="bs-label">Future fit</span><b>Timing and memory traits</b><p>Baseline, hesitation, practice and forgetting parameters</p></div>
<div class="bs-arrow"><span>sample</span></div>
<div class="bs-node bs-teal"><span class="bs-label">Future output</span><b>Calibrated cohorts</b><p>Trait distributions checked against human data</p></div>
</div>
<figcaption><strong>Figure 4.</strong> Source-authored diagram of the <a href="docs.topics.review-dataset.record.md.html#4-stage-2-human-calibration-pipeline">future calibration specification</a>; no human fit or validation is reported.</figcaption>
</figure>

The specified estimates include a 5th-percentile baseline, log-normal hesitation parameters, a practice-decay rate and a forgetting curve. Positive cognitive delays must be converted from milliseconds to seconds before taking logarithms. Handling non-positive delays, separating practice and strain effects, and estimating effort remain unspecified. A fit to observed delay alone cannot identify raw hesitation parameters.

### Statistical Validation:
The record specifies **two-sample Kolmogorov-Smirnov (KS) tests** as a future method. A $\chi^2$ test for discrete grade frequencies was an earlier page proposal and remains an unresolved choice, including its sampling assumptions and acceptance criteria. Neither test guarantees realistic learners. The calibration decision must establish latency and discrete-grade methods, sampling/dependence assumptions, data splits, practical discrepancy tolerances and uncertainty reporting before a fit can qualify. No human-fit or goodness-of-fit result is established by the recorded synthetic experiments; see [calibration limits](docs.topics.review-dataset.record.md.html#42-cohort-personas--distribution-sampling).

Source coverage for this explanation is the <a href="docs.topics.review-dataset.record.md.html#6-source-coverage-and-verification-limits">bounded audit at <code>788e060</code></a>. Tests were inspected, not executed; no generation, app export, human fit or goodness-of-fit check was run.

</section>
