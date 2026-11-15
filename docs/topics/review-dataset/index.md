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

## 1. Review Session Dataset Schema

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

Guided `new` and `learning` sessions have perfect accuracy and receive latency-based grades. They update model state but do not contribute to training loss. The same loss exclusion applies to unassisted rows with `t_days < 1`.

</section>

<section class="card" id="grading">

## 2. Automated Session Grading Function

<p class="bs-lead">Any first-attempt error gives Again; otherwise mean cognitive delay selects Easy, Good or Hard under TEMPO's grading policy.</p>

<figure id="fig-grading">
<div class="bs-grid g2" role="img" aria-label="Any first-attempt error gives Again. For a clean session, delay below 500 milliseconds gives Easy, 500 through 1800 gives Good, and above 1800 gives Hard.">
<div class="bs-part bs-orange"><h3>Any first-attempt error?</h3><p><strong>Yes → 1 · Again</strong></p><p>Retry time does not turn a failed first attempt into clean recall.</p></div>
<div class="bs-part bs-teal"><h3>No → compare mean delay</h3><p><strong>Below 500 ms → 4 · Easy</strong></p><p><strong>500–1800 ms → 3 · Good</strong></p><p><strong>Above 1800 ms → 2 · Hard</strong></p></div>
</div>
<figcaption><strong>Figure 1.</strong> Source-authored branches of the <a href="docs.topics.review-dataset.record.md.html#32-decision-logic">session grading policy</a>. These are configured thresholds, not fitted human-memory boundaries.</figcaption>
</figure>

[Figure 1](#fig-grading) puts correctness first. Latency distinguishes grades only after every first attempt is correct.


For a clean session, the model divides total latency by the number of repertoire moves ($M$) and subtracts the client's physical baseline. This normalizes the latency comparison; it does not make the entire grading process independent of line length.

$$\text{Average Delay per Move } \bar{\Delta} = \frac{\text{total\_time\_ms}}{M} - \text{baseline\_ms}$$

| Condition | Grade |
|---|---|
| Any first-attempt error | 1 — Again |
| Clean; mean cognitive delay below 500 ms | 4 — Easy |
| Clean; mean cognitive delay from 500 through 1800 ms | 3 — Good |
| Clean; mean cognitive delay above 1800 ms | 2 — Hard |

These thresholds are the package's [implemented grading policy](docs.topics.review-dataset.record.md.html#32-decision-logic), not a validated diagnosis of a person's memory. The [synthetic-client explanation](synthetic-clients.html#memory-dynamics) shows why longer lines have a lower clean-session probability under independent recall draws. The app's separate backend grading path is described in the [FSRS training record](docs.topics.fsrs-training.fsrs-training.md.html).

</section>

<section class="card" id="calibration">

## 3. Stage 2: Human Calibration Pipeline

<p class="bs-lead">Human calibration is a future specification; the package currently supplies trait-sampling hooks, without a fitted human cohort or validation result.</p>

[Figure 2](#fig-calibration) shows the specified calibration direction. Every stage awaits implementation and human evidence; the arrows do not describe an executed pipeline.

<figure id="fig-calibration">
<div class="bs-flow" role="img" aria-label="Future human calibration: collect human move telemetry, estimate latency and memory traits, then fit cohorts for synthetic trait sampling. No stage has a human-fit result.">
<div class="bs-node bs-violet"><span class="bs-label">Future input</span><b>Human telemetry</b><p>Move times, first-attempt errors and review history</p></div>
<div class="bs-arrow"><span>estimate</span></div>
<div class="bs-node bs-orange"><span class="bs-label">Future fit</span><b>Timing and memory traits</b><p>Baseline, hesitation, practice and forgetting parameters</p></div>
<div class="bs-arrow"><span>sample</span></div>
<div class="bs-node bs-teal"><span class="bs-label">Future output</span><b>Calibrated cohorts</b><p>Trait distributions checked against human data</p></div>
</div>
<figcaption><strong>Figure 2.</strong> Source-authored diagram of the <a href="docs.topics.review-dataset.record.md.html#4-stage-2-human-calibration-pipeline">future calibration specification</a>; no human fit or validation is reported.</figcaption>
</figure>

The specified estimates include a 5th-percentile baseline, log-normal hesitation parameters, a practice-decay rate and a forgetting curve. Positive cognitive delays must be converted from milliseconds to seconds before taking logarithms. Handling non-positive delays, separating practice and strain effects, and estimating effort remain unspecified. A fit to observed delay alone cannot identify raw hesitation parameters.

### Statistical Validation:
The record specifies **two-sample Kolmogorov-Smirnov (KS) tests** as a future method. A $\chi^2$ test for discrete grade frequencies was an earlier page proposal and remains an unresolved choice, including its sampling assumptions and acceptance criteria. Neither test guarantees realistic learners. No human-fit or goodness-of-fit result is established by the recorded synthetic experiments; see [calibration limits](docs.topics.review-dataset.record.md.html#42-cohort-personas--distribution-sampling).

</section>
