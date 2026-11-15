# Topic Record: Review Dataset Schema & Human Calibration Pipeline

## 1. Scope & Ownership

| Item | Canonical Owner |
|---|---|
| Technical specification & schema | `docs/topics/review-dataset/record.md` |
| Human-facing documentation & explanation | `docs/topics/review-dataset/index.md` |
| Synthetic client cognitive model | `docs/topics/synthetic-clients/record.md` (Topic 1) |
| Project context & product vocabulary | `docs/PROJECT_CONTEXT.md` |

This topic record specifies:
1. The **Review Session Dataset Schema** (the CSV interface capturing synthetic and human review telemetry).
2. The **Session Grading Function** (translating line accuracy and latency into FSRS grades).
3. The **Stage 2 Calibration Pipeline** (tuning synthetic client hyperparameters from empirical human testing data).

Status: the schema and grading function are implemented in
`ml/tempo_ml/simulator/grading.py`. Stage 2 below is a future specification;
the package implements trait sampling hooks, not human parameter estimation,
clustering or goodness-of-fit validation. Synthetic-only experiment results
are owned by the [FSRS training record](../fsrs-training/fsrs-training.md).

---

## 2. Review Session Dataset Schema

Review sessions in both Learning and Repeating modes log structured outcomes to a central practice dataset.

### 2.1 CSV Columns & Specifications

| Column Name | Type | Description | Permitted Values / Units |
|---|---|---|---|
| `agent_name` | String | Unique identifier of the synthetic agent or human player | e.g. `synth_blitzer_01`, `human_tester_04` |
| `opening_name` | String | Name of the opening line tested | e.g. `Ruy Lopez: Berlin Defense` |
| `review_status` | Enum | State/mode of the review session | `new`, `learning`, `review`, `relearning` |
| `t_days` | Float | Elapsed time since the previous review session for this line | $\ge 0.0$ (days; $0.0$ for `new`) |
| `grade` | Integer | Calculated FSRS session grade | `1` (Again), `2` (Hard), `3` (Good), `4` (Easy) |
| `total_time_ms` | Integer | Total elapsed wall-clock time across all repertoire moves | $\sum_{i=1}^M \text{final\_time\_ms}_i$ (milliseconds) |
| `accuracy` | Float | First-attempt move accuracy ratio across the line | $A \in [0.0, 1.0]$ ($1.0$ if no blunders) |

In the package, `total_time_ms` sums every attempt's latency, including
retries, rather than independently measured wall-clock time between session
start and finish. One repertoire move contributes its failed attempts and
its final attempt; accuracy still counts only the first attempt.
`new` and `learning` rows have perfect guided accuracy and are graded by
latency, but are excluded from training loss. Unassisted rows with
`t_days < 1` also update model state without contributing to the loss.

`opening_name` is not globally unique in the catalog. The package keeps
names unique within each client's sampled repertoire, so its trainer can
key a card by `(agent_name, opening_name)`. That sampling guarantee is not
an app-wide identity contract. The backend uses `line_id`; deciding how a
human-data training export retains that identity is still open. Hidden
state, including `line_id`, `p_clean` and stability, is in the separate
`ground_truth.csv`; it is not part of the seven-column telemetry schema.

**Decision needed:** how will human training rows retain catalog identity?
Options are a versioned telemetry schema with an explicit `line_id`, or a
separate identity map accompanying the unchanged seven-column export.
**Provisional recommendation:** use a versioned schema with explicit
`line_id` and key cards by `(agent_name, line_id)`, matching the backend's
stable catalog identity. This avoids relying on unique display names or
sidecar alignment. The export format and loader changes wait for agreement
on that schema; the current seven-column contract and experiment inputs
stay as recorded.

### 2.2 Review Status Definitions
- `new`: First exposure to an opening line.
- `learning`: Practicing the line with arrows/guidance enabled (Learning Mode).
- `review`: Unassisted spaced-repetition test (Repeating Mode).
- `relearning`: Spaced review following a recent blunder/lapse session.

---

## 3. The Session Grading Function

In TEMPO Repeating Mode, mistakes are immediately retracted without playing out. To evaluate memory consolidation, the grading function maps move accuracy and cognitive latency into the standard 4-point FSRS grading scale.

### 3.1 Normalization by Line Length

For a clean session, normalize latency over the number of repertoire moves
($M$) so the thresholds use average delay rather than total line duration:

$$\text{Average Move Latency } \bar{T} = \frac{\text{total\_time\_ms}}{M}$$

$$\text{Average Cognitive Delay } \bar{\Delta} = \bar{T} - \text{baseline\_ms}$$

Where $\text{baseline\_ms}$ represents the client's physical motor and board-scan latency floor.

This does not make the whole grading distribution independent of line
length: every move must be correct, so a line's clean-session probability
is R^M in the synthetic model.

### 3.2 Decision Logic

```text
if accuracy < 1.0 (one or more blunders occurred):
    grade = 1  # AGAIN (Lapse)
else:
    if bar_delta < 500 ms:
        grade = 4  # EASY (Fluent, automatic recall)
    elif 500 ms <= bar_delta <= 1800 ms:
        grade = 3  # GOOD (Normal recall latency)
    else:
        grade = 2  # HARD (Clean, but labored retrieval / hesitation)
```

#### Rationale:
- **Lapse Priority (Grade 1):** TEMPO's grading policy assigns *Again* after any first-attempt failure in Repeating Mode. This is the project's mapping from move attempts to a session rating; FSRS receives that rating rather than imposing this mapping itself.
- **Hesitation as Memory Strength:** For clean sessions, cognitive delay ($\bar{\Delta}$) differentiates effortless automaticity (*Easy*) from vulnerable, high-hesitation recall (*Hard*).

---

## 4. Stage 2: Human Calibration Pipeline

The synthetic client framework is designed to bootstrap initial ML training. In Stage 2, empirical human logs calibrate the synthetic hyperparameters so simulated clients faithfully mirror human memory and hesitation distributions.

```
+--------------------------+
|  Human Testing Telemetry  |
|  (Move times, blunders)  |
+------------+-------------+
             |
             v
+--------------------------+
|   Parameter Extraction   |
| (Baseline, μ, σ, α, F, C)|
+------------+-------------+
             |
             v
+--------------------------+
|    Cohort Clustering     |
| (Fast, Diligent, Casual) |
+------------+-------------+
             |
             v
+--------------------------+
| Calibrated Synth Clients |
|  (Digital twin cohorts)  |
+--------------------------+
```

### 4.1 Parameter Estimation Methodology

1. **Physical Baseline ($\text{baseline\_ms}$):**
   Estimated per human user from the 5th percentile ($P_5$) of move latencies on familiar lines, isolating pure motor/UI execution from cognitive retrieval.
2. **Cognitive Hesitation Distribution ($\mu, \sigma$):**
   The simulator's raw hesitation is in seconds, while telemetry is in
   milliseconds. Convert positive cognitive delays to seconds before taking
   logarithms: $\Delta_i = (T_i - \text{baseline\_ms}) / 1000$.
   The log-transformed delays $\ln(\Delta_i)$ are fitted to normal parameters:
   $$\hat{\mu} = \frac{1}{N}\sum \ln(\Delta_i), \quad \hat{\sigma} = \sqrt{\frac{1}{N-1}\sum (\ln(\Delta_i) - \hat{\mu})^2}$$
   Taking logarithms of milliseconds instead would shift $\hat{\mu}$ by
   $\ln(1000)$ and inflate generated hesitation by a factor of 1000.
   Treatment of non-positive delays, removal of practice/strain effects,
   and estimation of the effort parameter beta remain unspecified; fitting
   observed delay alone does not recover raw hesitation parameters.
3. **Practice Automaticity Rate ($\alpha$):**
   Fitted via non-linear least squares to the observed reduction in $\bar{\Delta}$ across review counts $n \in \{1, 2, 5, 10\}$.
4. **Forgetting Curve Parameters ($F, C$):**
   Estimated by grouping human review sessions across varying elapsed intervals $t$ and fitting recall success to the power law:
   $$R(t, S) = \left(1 + F \cdot \frac{t}{S}\right)^{-C}$$

### 4.2 Cohort Personas & Distribution Sampling

Rather than simulating one uniform average human, human testers are clustered (e.g. via Gaussian Mixture Models) into 3–4 behavioural cohorts:
- Synthetic clients draw their trait vectors $\theta \sim \mathcal{N}(\mu_{\text{cohort}}, \Sigma_{\text{cohort}})$ directly from these empirical clusters.
- Goodness-of-fit is validated using two-sample Kolmogorov-Smirnov tests comparing synthetic vs human hesitation distributions and grade frequencies.

This is a future validation method, not a guarantee of human
realism. The page also names a chi-squared test for grade frequencies;
that test is not specified here as an accepted requirement. Choosing the
test for discrete grade counts, its sampling assumptions and acceptance
criteria remains open. No such check has been executed by the package's
recorded synthetic training experiments.

**Decision needed:** which tests and acceptance criteria would qualify
human calibration? Options are the recorded KS approach for both signals,
or separate latency and discrete-grade methods, with chi-squared counts or
an exact/resampling alternative for grades according to sample size and
dependence. **Provisional recommendation:** specify latency and grade checks
separately; choose a count-aware method for grades after inspecting the
human sampling design. Agree practical discrepancy tolerances and
uncertainty reporting before fitting, rather than interpreting a
non-significant test alone as realism. No numerical tolerance is proposed
without human evidence. Implementing qualification checks or declaring
calibrated cohorts validated waits for agreement on the data split,
sampling assumptions, methods and acceptance criteria.

## Page presentation and numeric sources

The authored page separates the implemented session export and grading from
future human calibration. Inline source-authored diagrams in `index.md` use
section 3.2 for the grading branches and section 4 for the future pipeline;
neither claims a completed human calibration.

| Displayed numbers or construction | Canonical source |
|---|---|
| Seven telemetry columns; grade values 1/2/3/4; accuracy 0 through 1; t_days at least 0 | Section 2.1 |
| Guided accuracy 1; rows below 1 day excluded from loss | Section 2.1 implementation clarification |
| Again after any first-attempt error; Easy below 500 ms; Good 500 through 1800 ms; Hard above 1800 ms | Section 3.2 |
| Stage 2; chi-squared exponent 2 | Section 4 and its unresolved validation-method clarification |
| 5th-percentile physical baseline estimate | Section 4.1, Physical Baseline; future calibration specification, not a completed measurement |
| CSV illustration: 2.4 days / grade 3 / 3420 ms / accuracy 1.0; 0.5 days / grade 1 / 8940 ms / accuracy 0.75; 5.1 days / grade 4 / 1980 ms / accuracy 1.0 | Existing page's labelled illustrative rows; invented examples, not observations or grade-calculation tests, because move counts and baselines are not supplied |

The illustrative CSV block is retained verbatim during the presentation
update. Its identifiers and numbers do not establish collected human data.
Figure and chapter numbers are presentation identifiers.
