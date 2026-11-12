+++
toc = []
title = "Review Dataset Schema & Human Calibration Pipeline"
slug = "review-dataset"
brand_sub = "session telemetry · FSRS grading · human calibration"
components = ["toc", "nav", "code", "filelinks"]
page_css = ["build-sheet.css"]
math = true
+++

# Review Dataset Schema & Human Calibration Pipeline

<section class="card" id="schema">

## 1. Review Session Dataset Schema

<p class="bs-lead">Every opening session logs structured telemetry capturing line identity, review state, recall accuracy, elapsed wall-clock time, and FSRS grade.</p>

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
- **`total_time_ms`:** Cumulative session time across all repertoire moves (including physical baseline).
- **`accuracy`:** First-attempt accuracy ratio across the line ($1.0$ for clean runs).

</section>

<section class="card" id="grading">

## 2. Automated Session Grading Function

<p class="bs-lead">A player who hesitates for 8 seconds before making the right move was on the verge of forgetting it. Hesitation latency directly informs the grade.</p>

To grade fairly across lines of varying depth, total time is normalized across the number of repertoire moves ($M$):

$$\text{Average Delay per Move } \bar{\Delta} = \frac{\text{total\_time\_ms}}{M} - \text{baseline\_ms}$$

```python
def calculate_session_grade(blunder_count: int, total_time_ms: int, num_moves: int, baseline_ms: int) -> int:
    # 1. Any lapse in Repeating Mode triggers an immediate Again
    if blunder_count > 0:
        return 1  # AGAIN

    # 2. Normalize cognitive delay over line depth
    avg_move_time = total_time_ms / num_moves
    cognitive_delay = avg_move_time - baseline_ms

    # 3. Grade based on cognitive hesitation
    if cognitive_delay < 500:
        return 4  # EASY: effortless automaticity
    elif cognitive_delay <= 1800:
        return 3  # GOOD: standard recall
    else:
        return 2  # HARD: labored retrieval, memory is tenuous
```

</section>

<section class="card" id="calibration">

## 3. Stage 2: Human Calibration Pipeline

<p class="bs-lead">Empirical gameplay logs from human team members are analyzed to tune synthetic parameters, creating digital twin cohorts.</p>

```
[Human Gameplay Logs]
       │
       ▼
[Parameter Extraction] ──► Baseline: 5th percentile reaction time
                       ──► Hesitation: Log-normal MLE fit (μ, σ)
                       ──► Automaticity: Latency decay slope (α)
                       ──► Retention: Power-law forgetting curve (F, C)
       │
       ▼
[Persona Clustering]   ──► Cluster players into Fast, Balanced, Diligent cohorts
       │
       ▼
[Calibrated Agents]    ──► Synthetic clients sample from real human distributions
```

### Statistical Validation:
Calibrated synthetic data is checked against human telemetry using **two-sample Kolmogorov-Smirnov (KS) tests** on reaction times and $\chi^2$ frequency tests on grade distributions, guaranteeing that synthetic training data accurately mirrors real human learners.

</section>
