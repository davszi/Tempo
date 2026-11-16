# Topic Record: Review Dataset Schema & Human Calibration Pipeline

## 1. Scope & Ownership

| Item | Canonical Owner |
|---|---|
| Technical specification & schema | `docs/topics/review-dataset/record.md` |
| Human-facing documentation & explanation | `docs/topics/review-dataset/index.md` |
| Synthetic client cognitive model | `docs/topics/synthetic-clients/record.md` (Topic 1) |
| Session grading function (decided rule) | `docs/topics/session-grading/session-grading.md` |
| Project context & product vocabulary | `docs/PROJECT_CONTEXT.md` |

This topic record specifies:
1. The **Review Session Dataset Schema** (the CSV interface capturing synthetic and human review telemetry).
2. The **grading inputs the export carries**, the earlier grading rule still implemented, and the synthetic evidence gathered while the new rule was chosen (section 3). The decided rule itself is specified in the [session grading record](../session-grading/session-grading.md).
3. The **Stage 2 Calibration Pipeline** (tuning synthetic client hyperparameters from empirical human testing data).

Status: the schema and the earlier grading rule are implemented in
`ml/tempo_ml/simulator/grading.py`; the grading rule decided on 2026-11-16
is specified in the [session grading record](../session-grading/session-grading.md)
and not yet implemented (section 3). Stage 2 below is a future specification;
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
| `total_time_ms` | Integer | Sum of recorded attempt latencies across repertoire moves | $\sum_{i=1}^M \text{final\_time\_ms}_i$ (milliseconds; each move includes retries) |
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

The grading function maps a finished Repeating review into the 4-point FSRS
scale. **The decided rule is specified in the
[session grading record](../session-grading/session-grading.md)** (decided
2026-11-16): mistake limits by line length (0 for 3 moves, 1 for 4–7, 2 for
8–12, 3 for 13 or more), Easy only without mistakes, and fixed time bands
(1500 / 3500 / 8000 ms, each move capped at 20000 ms) on browser-measured
times of first-try correct moves, without the line's first move and without
a baseline. That record owns the rule, its rationale, test vectors,
implementation targets, open items and validation plan.

**Implementation status.** Not implemented. `ml/tempo_ml/simulator/grading.py`
and the app (`backend/ml_engine.py`, see
[system architecture](../system-architecture/system-architecture.md#initial-card-grading-and-update))
still apply the earlier rule (section 3.2). All recorded synthetic datasets
and results were graded with it.

This section keeps what belongs to the session export: the grading inputs
the export carries (3.1), the earlier rule (3.2), the synthetic timing model
(3.3), the synthetic clients' traits (3.4) and the synthetic evidence
gathered before the rule was decided (3.5).

### 3.1 Grading inputs in the export

The seven-column export carries `accuracy` and `total_time_ms`
(section 2.1). They are not enough to apply the decided rule: it needs the
line's move count `M`, the mistake count `k` and the mean of the capped
times of first-try correct moves without the first move. `total_time_ms`
includes retries and the first move, and `M` is not exported, so a dataset
cannot be regraded with the decided rule from the CSV alone. Adding these
inputs to the export is an open item of the
[session grading record](../session-grading/session-grading.md#63-exported-inputs).

### 3.2 The earlier rule (still implemented)

Any first-attempt error gives Again. Otherwise the mean time per move minus
the player's physical baseline, `total_time_ms / M − baseline_ms`, gives
Easy below 500 ms, Good from 500 to 1,800 ms and Hard above 1,800 ms. The
simulator subtracts each client's `baseline_ms`; the web app uses a baseline
of zero.

### 3.3 Where the time per move comes from (synthetic clients)

Move times come from `simulator/recall.py` (`sample_move_time_ms`); the
latency model is section 3.4 of the
[synthetic-client record](../synthetic-clients/record.md). In a clean session
every move is correct on its first attempt, so each move has exactly one
sampled time:
baseline_ms + 1000·H·exp(β(1−R))/(1 + α·reps), with H ~ Lognormal(μ, σ) in
seconds. The mean time per move is therefore

$$\bar{T} = \text{baseline\_ms} + \frac{1}{M}\sum_{i=1}^{M} 1000\,H_i\,e^{\beta(1-R)}\frac{1}{1+\alpha\,\text{reps}}$$

Each factor moves the time:

- The baseline adds the player's physical move time to every move; under
  this rule a faster-handed player gets faster grades.
- Lower recall R raises the time through exp(β(1−R)); high-effort players
  (large β) slow down most.
- More practice (reps) divides the hesitation by 1 + α·reps. reps rises by
  1 after a clean session and falls by 2 after a blunder (synthetic-client
  record, section 3.5).
- μ sets the player's typical speed; H's random draw makes the time vary
  between sessions, less so on longer lines because M draws are averaged.
- After a mistake the retry attempts add their time to the total, so a
  session with mistakes also has a longer mean time. Learning sessions are
  timed with R = 1.

Illustration (formula arithmetic, not a measurement): the expected mean time
per move, baseline_ms + 1000·exp(μ + σ²/2)·exp(β(1−R))/(1 + α·reps), at each
benchmark profile's mean traits (synthetic-client record, section 4).

| Profile | R = 1, reps 0 | R = 0.9, reps 0 | R = 0.7, reps 0 | R = 0.7, reps 5 |
|---|---|---|---|---|
| Blitzer | 827 ms | 852 ms | 905 ms | 469 ms |
| Balanced | 1187 ms | 1280 ms | 1497 ms | 832 ms |
| Diligent | 1815 ms | 2168 ms | 3157 ms | 1768 ms |

Individual clients' traits are spread around these means and each session
draws H afresh, so actual times scatter around these values.

### 3.4 Trait values of the synthetic clients

Each client of the generator
(`build_plans`) draws its traits from a normal distribution around its
profile's mean (synthetic-client record, section 4) with the configured
standard deviations (section 9), then `clamp_traits` limits them to the
allowed ranges (section 3.1). The last columns are the minimum and maximum
over the 300 clients of the 2026-11-13 multiplicative-memory run
(`ml/data/fsrs-synthetic-v2/train/clients.csv`, hashes in that experiment's
`dataset_MANIFEST.txt`), measured on 2026-11-16:

| Trait | Meaning | Blitzer / Balanced / Diligent mean | Spread (sd) | Allowed | Blitzer range | Balanced range | Diligent range |
|---|---|---|---|---|---|---|---|
| baseline_ms | physical floor added to every move | 220 / 300 / 380 ms | 25 ms | 150–500 ms | 151–277 ms | 240–355 ms | 303–467 ms |
| μ | log of typical hesitation in seconds; typical hesitation e^μ | −0.6 / −0.2 / 0.3 | 0.15 | any | −0.97 to −0.13 | −0.53 to 0.11 | −0.16 to 0.69 |
| σ | spread of hesitation draws | 0.45 / 0.40 / 0.35 | 0.05 | > 0 | 0.33–0.54 | 0.27–0.52 | 0.22–0.49 |
| β | effort: slowdown when recall is weak | 0.4 / 1.0 / 2.2 | 0.2 | ≥ 0 | 0–0.86 | 0.50–1.44 | 1.66–2.60 |
| α | practice speed-up per repetition | 0.35 / 0.25 / 0.20 | 0.04 | 0.1–0.5 | 0.25–0.46 | 0.18–0.37 | 0.10–0.30 |
| C | forgetting power | 0.65 / 0.50 / 0.35 | 0.05 | > 0 | 0.54–0.80 | 0.38–0.66 | 0.25–0.49 |

In that run one client's α sat on the lower limit 0.1 and two clients' β on
0; no baseline reached a limit. The typical hesitation e^μ is 549, 819 and
1350 ms at the three profile means.

### 3.5 Evidence for choosing the boundaries

Gathered on 2026-11-16 before the rule was decided. The candidate time
boundaries below (800 / 2100 ms) were superseded by the decided bands of the
[session grading record](../session-grading/session-grading.md#34-time-bands);
the figures remain valid as a synthetic comparison with the earlier rule.

**Time boundaries.** Measured on 2026-11-16 from the 76,287 clean Repeating sessions of the
2026-11-13 multiplicative-memory run (`ml/data/fsrs-synthetic-v2/train/`,
all 300 clients; times and grades recomputed from `sessions.csv`,
`ground_truth.csv` and `clients.csv`). Share of Easy / Good / Hard:

| Rule | Easy | Good | Hard | Blitzer Easy / Hard | Balanced Easy / Hard | Diligent Easy / Hard |
|---|---|---|---|---|---|---|
| Earlier rule (baseline removed, 500 / 1800 ms), as recorded in the data | 31.5% | 65.1% | 3.4% | 67.2% / 0.0% | 25.9% / 0.1% | 1.6% / 9.9% |
| Mean time per move, earlier boundaries 500 / 1800 ms | 5.8% | 85.5% | 8.7% | 17.4% / 0.0% | 0.1% / 0.9% | 0.0% / 25.0% |
| Mean time per move, candidate 800 / 2100 ms | 35.3% | 60.6% | 4.1% | 79.6% / 0.0% | 26.0% / 0.1% | 0.4% / 12.1% |

Keeping the earlier boundaries would make Easy rare, because they were set
for hesitation without the physical move. Raising both by 300 ms, about the
clients' median baseline (302 ms), keeps the overall mix close to the
earlier one and changes 6.5% of clean grades; the shifts left are the ones
the new rule intends (fast-handed clients more Easy, slow ones more Hard).
This is a synthetic comparison only: it shows how the candidate relates to
the earlier rule, not where human recall changes. Setting the intervals
needs real mean times per move from the app. Changing the rule also changes
the grades in generated data, so datasets and trained weights would be
regenerated.

**Accuracy in the synthetic data.** From the same run's 123,891 Repeating
sessions (all 300 clients, including the same-day tests; graded by the
earlier rule): mistakes per review were 0 in 61.6%, 1 in 24.3%, 2 in 9.3%,
3 in 3.3% and 4 or more in 1.5%. Accuracy was at least 0.9 in 65.2% of
reviews, at least 0.8 in 83.7%, at least 0.75 in 90.2% and at least 0.5 in
99.1%. A single mistake leaves a median accuracy of 0.83, but 0.67 on 2–3
move lines, 0.80 on 4–5, 0.83 on 6–7, 0.88 on 8–9 and 0.91 on 10 or more:
an accuracy boundary would treat one slip on a short line as far worse than
on a long one. Under the earlier rule every one of the 38.4% of reviews with
a mistake is Again. Synthetic only; human accuracy is unmeasured.

With FSRS hidden memory the grade also changes the memory update
(synthetic-client record, section 7); with multiplicative memory it does not.

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

## 5. Generated files and producer boundaries

The seven-column header is a shared interface, not proof that producers
model the same population or collection policy. [Synthetic Players](../synthetic-clients/record.md#9-practice-policy-generation-and-demo-producer)
owns those mechanisms; [FSRS Training](../fsrs-training/fsrs-training.md#fitting-and-state-replay)
owns masking and fitting.

| File / producer | Content and interpretation |
|---|---|
| Offline `sessions.csv` | Exactly section 2's seven columns, chronological per client; one row per guided or unassisted session |
| `ground_truth.csv` | Hidden row-aligned sidecar: agent/archetype/side/line ID/name/move count, simulation day/mode/status/elapsed/grade/accuracy/blunders, per-move R, clean chance, stability before/after and familiarity before/after |
| `clients.csv` | Traits (baseline, mu, sigma, beta, alpha, C, derived F), archetype/side, repertoire size, attendance probability and review budget; synthetic parameters, not human observations |
| `repertoires.csv` | Agent, catalog line ID, display name, family and side-specific move count |
| `memory_weights.csv` | Written for FSRS-hidden-memory runs: agent plus w0–w20; hidden truth, not fitted weights; see output-directory precondition below |
| `manifest.json` | Producer/config/model/retry cap, counts, catalog content identity, CSV hashes, source/environment and elapsed generation time |
| Backend demo CSV | Same seven header fields from `backend/synthetic_clients.py`; no truth sidecars or manifest; counts all plies rather than player's repertoire moves |

Generation should use a fresh output directory when changing models or
producing an independently identified dataset. `generate.py` conditionally
writes `memory_weights.csv` for FSRS hidden memory, does not delete a pre-existing
copy for multiplicative memory, and hashes every CSV already in the output
directory into the manifest. Reusing a previous FSRS directory can therefore
retain and hash stale hidden weights or other unrelated CSV files. This is a
source-control-flow inference, not evidence that any retained historical run
was contaminated. The manifest alone does not prove every listed file was
produced by its latest invocation.

Offline `p_clean` is R raised to repertoire move count for repeating sessions
and 1 for guided sessions. Hidden R/stability/reps are unavailable from human
telemetry. The producer rounds `t_days` to four decimals, simulation day to
six, hidden probabilities/stabilities to six and total latency to integer
milliseconds. Grading uses the underlying unrounded attempt sum first.
Move events exist in memory but are not exported here, so the seven columns
cannot reconstruct individual attempt latencies, move order or whether the
final retry succeeded.

`SessionRecord` validates status, nonnegative elapsed/time, grade 1–4 and
accuracy in [0,1]. `calculate_session_grade` requires positive move count
and nonnegative blunders. Move count and physical baseline are additional
grading inputs, absent from the seven-column row. The trainer reads CSV
values directly rather than validating arbitrary imports with this class.

The backend demo emits `new`, `review` and `relearning`, not guided
`learning`. First exposure uses R = 1, then scheduling comes from the backend
engine. Duplicate catalog names receive `[line ID]`, whereas offline
repertoire selection rejects duplicates per client. Neither is an agreed
human identity export. Browser/API submissions and persisted timestamps
belong to [App & practice](../app-practice/app-practice.md); no completed
app-to-training export or human calibration pipeline is established by the
inspected ML code.

## 6. Source coverage and verification limits

The bounded 2026-11-15 source pass at
`788e06039dd2869b23261dd80ea8fc49367ab33c` read every package file, four
configs, package metadata/tests and `backend/synthetic_clients.py`.
It filled output/sidecar, rounding, validation and producer boundaries,
keeping future calibration distinct from implementation. No additional
telemetry topic is needed for this scope; storage belongs to Catalog & data
and app submission to App & practice.

| Source / symbols | Canonical section or owner |
|---|---|
| `ml/tempo_ml/simulator/grading.py`: `calculate_session_grade`, `CSV_COLUMNS`, `REVIEW_STATUSES`, `SessionRecord`, `write_sessions_csv` | Sections 2–3 and 5 |
| `simulator/clients.py`: `_finish`, `SessionOutcome` | Section 5 rounding/observable boundary; Synthetic Players owns memory |
| `simulator/generate.py`: `GROUND_TRUTH_COLUMNS`, `generate` output writers/manifest | Section 5; Synthetic Players owns collection |
| `fsrs/model.py`: `load_cards`, `Cards.row`, `loss_mask` | Section 2 identity limits; FSRS Training owns ingestion/masking |
| `evaluate/metrics.py`: `Truth.grid` | Section 5 row alignment; FSRS Training owns scoring |
| `backend/synthetic_clients.py`: `CSV_FIELDS`, `simulate_line`, `read_lines`, `write_dataset` | Section 5; Synthetic Players owns producer simulation |
| `ml/tests/test_simulator.py`: grading thresholds, record fields, output header/identity | Sections 2–3 and 5; inspected assertions only |
| `ml/tests/test_trainers.py`: `test_load_cards_and_masks` | FSRS Training replay contract; excluded rows still update state |

Tests were inspected, not executed. No generation, training, app session,
human fitting or goodness-of-fit check ran. Existing assertions cover grade
boundaries and example exports, not human calibration, a stable human
identity export, retry completion or arbitrary imported CSV chronology and
sidecar alignment. These gaps remain future work or explicit decisions.

## Page presentation and numeric sources

The authored page separates the implemented session export and grading from
future human calibration. Inline source-authored diagrams in `index.md` use
section 3.2 for the grading branches and section 4 for the future pipeline;
neither claims a completed human calibration.

| Displayed numbers or construction | Canonical source |
|---|---|
| Seven telemetry columns; grade values 1/2/3/4; accuracy 0 through 1; t_days at least 0 | Section 2.1 |
| Guided accuracy 1; rows below 1 day excluded from loss | Section 2.1 implementation clarification |
| Decided rule summary: mistake limits 0/1/2/3 by 3 \| 4–7 \| 8–12 \| 13+; 1500 / 3500 / 8000 ms bands; 20000 ms cap; not implemented | Section 3 introduction; canonical values in the [session grading record](../session-grading/session-grading.md) sections 3.2 and 3.4 |
| Earlier rule: any mistake gives Again; 500 / 1,800 ms after baseline subtraction | Section 3.2 |
| Export lacks `M`, `k` and the timed-move mean needed by the decided rule | Section 3.1 |
| Time-per-move formula; reps +1 / −2; expected mean time per move per profile at R = 1, 0.9, 0.7 and reps 0, 5 | Section 3.3; formula arithmetic at the benchmark profiles' mean traits, not measurements |
| Trait means, standard deviations and allowed ranges; typical hesitation 549 / 819 / 1350 ms; web baseline zero | Section 3.4, from synthetic-client record sections 3.1, 4 and 9 and the system-architecture record |
| Trait minimum–maximum per profile over 300 clients; one α at 0.1, two β at 0 | Section 3.4; measured on the 2026-11-13 run's generated `clients.csv` |
| 76,287 clean sessions; grade shares per rule and profile; 6.5% changed; earlier 500 / 1800 ms; candidate 800 / 2100 ms (superseded by the decided bands); median baseline 302 ms | Section 3.5; measured on the 2026-11-13 run's generated data |
| 123,891 Repeating sessions; mistakes per review 0/1/2/3/4+; accuracy shares at 0.9/0.8/0.75/0.5; one-mistake median accuracy overall and by line length; 38.4% with a mistake | Section 3.5; measured on the 2026-11-13 run's generated data |
| Stage 2; chi-squared exponent 2 | Section 4 and its unresolved validation-method clarification |
| 5th-percentile physical baseline estimate | Section 4.1, Physical Baseline; future calibration specification, not a completed measurement |
| CSV illustration: 2.4 days / grade 3 / 3420 ms / accuracy 1.0; 0.5 days / grade 1 / 8940 ms / accuracy 0.75; 5.1 days / grade 4 / 1980 ms / accuracy 1.0 | Existing page's labelled illustrative rows; invented examples, not observations or grade-calculation tests, because move counts and baselines are not supplied |

The illustrative CSV block is retained verbatim during the presentation
update. Its identifiers and numbers do not establish collected human data.
Figure and chapter numbers are presentation identifiers.
