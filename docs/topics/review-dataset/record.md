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

### 2.2 Review Status Definitions
- `new`: First exposure to an opening line.
- `learning`: Practicing the line with arrows/guidance enabled (Learning Mode).
- `review`: Unassisted spaced-repetition test (Repeating Mode).
- `relearning`: Spaced review following a recent blunder/lapse session.

---

## 3. The Session Grading Function

In TEMPO Repeating Mode, mistakes are immediately retracted without playing out. To evaluate memory consolidation, the grading function maps move accuracy and cognitive latency into the standard 4-point FSRS grading scale.

### 3.1 Normalization by Line Length

To ensure grading is invariant to variation depth, latency is normalized over the number of repertoire moves ($M$):

$$\text{Average Move Latency } \bar{T} = \frac{\text{total\_time\_ms}}{M}$$

$$\text{Average Cognitive Delay } \bar{\Delta} = \bar{T} - \text{baseline\_ms}$$

Where $\text{baseline\_ms}$ represents the client's physical motor and board-scan latency floor.

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
- **Lapse Priority (Grade 1):** Any blunder in Repeating Mode indicates the memory trace failed retrieval threshold; FSRS requires an *Again* rating to contract the scheduling interval.
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
   Computed on cognitive delays $\Delta_i = T_i - \text{baseline\_ms}$. The log-transformed delays $\ln(\Delta_i)$ are fitted to normal parameters:
   $$\hat{\mu} = \frac{1}{N}\sum \ln(\Delta_i), \quad \hat{\sigma} = \sqrt{\frac{1}{N-1}\sum (\ln(\Delta_i) - \hat{\mu})^2}$$
3. **Practice Automaticity Rate ($\alpha$):**
   Fitted via non-linear least squares to the observed reduction in $\bar{\Delta}$ across review counts $n \in \{1, 2, 5, 10\}$.
4. **Forgetting Curve Parameters ($F, C$):**
   Estimated by grouping human review sessions across varying elapsed intervals $t$ and fitting recall success to the power law:
   $$R(t, S) = \left(1 + F \cdot \frac{t}{S}\right)^{-C}$$

### 4.2 Cohort Personas & Distribution Sampling

Rather than simulating one uniform average human, human testers are clustered (e.g. via Gaussian Mixture Models) into 3–4 behavioural cohorts:
- Synthetic clients draw their trait vectors $\theta \sim \mathcal{N}(\mu_{\text{cohort}}, \Sigma_{\text{cohort}})$ directly from these empirical clusters.
- Goodness-of-fit is validated using two-sample Kolmogorov-Smirnov tests comparing synthetic vs human hesitation distributions and grade frequencies.
