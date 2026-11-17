# Topic Record: Synthetic Client Behavioral & Cognitive Model

## 1. Scope & Ownership

| Item | Canonical Owner |
|---|---|
| Technical specification & parameters | `docs/topics/synthetic-clients/record.md` |
| Human-facing documentation & explanation | `docs/topics/synthetic-clients/index.md` |
| Project context & product vocabulary | `docs/PROJECT_CONTEXT.md` |
| Review session dataset | `docs/topics/review-dataset/record.md` (Topic 2) |
| Session grading function (decided rule) | `docs/topics/session-grading/session-grading.md` |

This record specifies the behavioral, cognitive, and latency simulation engine for **Synthetic Clients** in TEMPO. Synthetic clients generate simulated practice histories (repetitions, move accuracy, and move hesitation times) across opening lines to train and calibrate the Review Planner and FSRS without cold-start dependencies on human user data.

Status: the demo specification below is implemented by the offline package
`ml/tempo_ml/` with the additions and limits in section 6. It defines a
synthetic model; its realism for human players has not been validated.
Stage 2 human calibration is future work, not a completed measurement.

---

## 2. Settled Decisions (Demo Specification)

1. **Dual-Signal Telemetry:** Every move played produces two explicit signals:
   - **Move Accuracy:** Binary correctness relative to the line's repertoire move.
   - **Hesitation Time:** Total latency in milliseconds, comprising physical motor baseline and cognitive search latency.
2. **Effort Decoupled from Accuracy:** Cognitive effort ($\beta$) influences hesitation and cognitive strain, but does **not** directly boost accuracy. Move accuracy is governed purely by memory Retrievability ($R$).
3. **Practice Fluency Decay:** Repeated successful reviews of an opening line reduce cognitive hesitation toward physical baseline latency via a dedicated practice multiplier ($m_{\text{practice}}$).
4. **Soft Penalty on Blunder:** A mistake or blunder during Repeating Mode decrements accumulated familiarity by a 2-step penalty rather than hard-resetting all motor automaticity to zero.
5. **Context Penalties Deferred:** Position-specific multipliers ($m_{\text{depth}}$ and $m_{\text{sharpness}}$) are formally specified as future extensions and omitted from the initial demo.

---

## 3. Mathematical Formulation

### 3.1 Client Traits (Hyperparameters)

Each synthetic client instance is defined by a vector of cognitive traits:

$$\theta = \langle \text{baseline\_ms}, \mu, \sigma, \beta, \alpha, F, C \rangle$$

- $\text{baseline\_ms} \in [150, 500]$: Physical motor, visual processing, and interface latency floor (ms).
- $\mu \in \mathbb{R}$: Mean of the logarithm of raw cognitive hesitation measured in seconds (the median raw hesitation is $e^\mu$ seconds).
- $\sigma > 0$: Shape / dispersion parameter of the raw cognitive hesitation distribution.
- $\beta \ge 0$: Effort parameter dictating cognitive strain under memory uncertainty.
- $\alpha \in [0.1, 0.5]$: Practice automaticity rate (how rapidly repetitions eliminate cognitive delay).
- $F > 0, C > 0$: Forgetting curve scaling factor and decay power.

---

### 3.2 Memory Retrievability ($R$)

Following the DSR power-law formulation in modern FSRS:

$$R(t, S) = \left(1 + F \cdot \frac{t}{S}\right)^{-C}$$

- $t$: Elapsed time since the previous review of this line (in days).
- $S$: Current memory stability of the opening line (days until $R = 0.9$).
- $C$: Personal forgetting curve decay power.
- $F$: Calibration factor satisfying $F = 0.9^{-1/C} - 1$.

---

### 3.3 Move Accuracy Decision

When tested on a repertoire move in Repeating Mode:

$$P(\text{Move is Repertoire Move}) = R(t, S)$$
$$P(\text{Blunder / Wrong Move}) = 1 - R(t, S)$$

- If the sampled outcome is correct, the move is placed and the session advances.
- If a blunder occurs, TEMPO Repeating Mode rules apply: the wrong move is not played out on the board; it is immediately retracted for retry.

---

### 3.4 Hesitation Latency Model

Move latency represents the sum of physical baseline reaction and scaled cognitive strain:

$$\text{final\_time\_ms} = \text{baseline\_ms} + \text{total\_hesitation\_ms}$$

Where:

$$\text{raw\_hesitation} \sim \text{Lognormal}(\mu, \sigma) \quad \text{(seconds)}$$

$$\text{cognitive\_strain} = \exp\big(\beta \cdot (1 - R)\big)$$

$$m_{\text{practice}} = \frac{1}{1 + \alpha \cdot \text{reps}}$$

$$\text{total\_hesitation\_ms} = (\text{raw\_hesitation} \times 1000) \times \text{cognitive\_strain} \times m_{\text{practice}}$$

#### Boundary Dynamics:
- **At high retrievability ($R \to 1.0$):** $(1 - R) \to 0 \implies \text{cognitive\_strain} \to 1.0$.
- **At high repetition ($reps \gg 1$):** $m_{\text{practice}} \to 0 \implies \text{total\_hesitation\_ms} \to 0$. The move executes at pure motor baseline ($\text{baseline\_ms}$).
- **Under forgetting ($t \gg S, R \ll 1$):** $\text{cognitive\_strain}$ exponentially amplifies hesitation scaled by client effort $\beta$.

---

### 3.5 Practice Accumulation & Lapse Transitions

After a review session for an opening line:

$$\text{reps}_{k+1} = \begin{cases} \text{reps}_k + 1 & \text{if the review passed (Hard, Good or Easy)} \\ \max(0, \text{reps}_k - 2) & \text{if it was graded Again} \end{cases}$$

Since 2026-11-16 a lapse is a review graded Again under the
[session grading rule](../session-grading/session-grading.md); a review with
mistakes within the line's limit is a pass. Before, any first-attempt mistake
was a lapse.

---

## 4. Benchmark Archetypes (Stage 1 Demo Profiles)

| Parameter | Fast / Impulsive | Balanced / Average | Diligent / Deliberate |
|---|---|---|---|
| `baseline_ms` | 220 ms | 300 ms | 380 ms |
| $\mu$ | -0.6 | -0.2 | 0.3 |
| $\sigma$ | 0.45 | 0.40 | 0.35 |
| $\beta$ (Effort) | 0.4 | 1.0 | 2.2 |
| $\alpha$ (Practice rate) | 0.35 | 0.25 | 0.20 |
| $C$ (Decay) | 0.65 | 0.50 | 0.35 |

---

## 5. Deferred Context Extensions (Post-Demo Scope)

In advanced iterations, context multipliers will be reintroduced to account for board complexity:

$$\text{total\_hesitation\_ms} = (\text{raw\_hesitation} \times 1000) \times \text{cognitive\_strain} \times m_{\text{practice}} \times m_{\text{depth}} \times m_{\text{sharpness}}$$

1. **Depth Multiplier ($m_{\text{depth}}$):**
   $$m_{\text{depth}} = 1.0 + (0.02 \times \text{ply\_number})$$
2. **Sharpness Multiplier ($m_{\text{sharpness}}$):** Evaluated from tactical volatility (e.g. branching factor and engine evaluation delta across alternatives).

## 6. Implementation and open choices

Source inspection: `ml/tempo_ml/simulator/clients.py` implements traits,
archetypes, per-line memory and guided/unassisted sessions;
`recall.py` implements per-attempt latency and recall; `practice.py` owns
the data-collection policy. Sections 7–9 below own hidden stability,
collection policy and producer differences. The [FSRS training record](../fsrs-training/fsrs-training.md)
owns fitting, evaluation and historical results.

- Every repertoire move has an independent first-attempt recall draw with
  the same line-level R. A review passes with at most L(M) mistakes, so its
  chance is `p_pass(R, M)` (`ml/tempo_ml/pass_chance.py`), where M is the
  number of the player's moves. Hidden stability and familiarity remain per
  line, not separate states for each move.
- Learning follows the arrows: every move is correct and latency uses
  R = 1. Guided sessions also increment familiarity and update hidden
  stability. The generator adds an unassisted test after the guided session
  duration plus three minutes. These are package policy additions to the
  formulas above, not evidence about human learning.
- `recall.py`, `play_move`, caps attempts at five by default. If the final
  draw fails, no successful final attempt is represented; the move/session
  nevertheless advances and hidden memory updates. The client docstring
  assumes the move is found on that last attempt, but the implementation
  does not force that outcome. Whether to force success, keep retrying or
  represent incomplete sessions remains an unresolved implementation choice;
  the cap is not part of the accepted demo specification.
  **Decision needed:** what does exhausting the retry cap mean? Options are
  to force the final attempt to succeed, continue until a correct draw, or
  represent an incomplete session. **Provisional recommendation:** represent
  incomplete sessions explicitly, preserving the bounded attempt count and
  observed failures rather than claiming an unobserved success. This needs
  an agreed completion field and rules for grading and memory updates;
  changing those behaviors, the telemetry schema and affected datasets waits
  for that decision. Existing experiment outputs retain their original
  retry semantics.
- The current CSV omits individual move events; `total_time_ms` includes
  all attempted moves, including retries. Accuracy counts only first attempts.
  The grade uses each move's first-attempt time (`grading.calculate_session_grade`).
  The [review dataset record](../review-dataset/record.md) owns those fields.
- Archetype values are benchmark settings, not fitted human cohorts.
  `TraitDistribution` supplies bounded multivariate-normal sampling as a
  calibration hook; no parameter-estimation or human-fit validation pipeline
  is implemented in `ml/tempo_ml/`.

The separate `backend/synthetic_clients.py` is a demo telemetry generator,
not this package: it counts all plies, uses the backend scheduler and one
successful retry after a failed first attempt. Do not treat its output as
one of the package experiment datasets or as a validated human calibration.

## 7. Offline simulator and hidden memory

Code: `ml/tempo_ml/`; setup: [ML development](../../development/ml.md).
Since 2026-11-16 FSRS memory is the only hidden memory
([move recall record, section 3.1](../move-recall/move-recall.md#31-fsrs-memory-is-the-only-hidden-memory-model)):

| Implementation | Initial state and updates |
|---|---|
| `simulator/memory/fsrs.py`, `FSRSMemory`; state in `simulator/memory/state.py`, `LineMemory` | First grade initializes S and D. Later sessions below one elapsed day use short-term stability; later sessions use the recall update for Hard, Good and Easy and the forget update for Again. After Again, S is clamped to min(previous S, max(1 day, updated S)) |

The multiplicative model (`memory/multiplicative.py`, `MultiplicativeStability`;
first exposure S = 1 day, clean session S × (1 + 1.5·exp(2(1−R))), lapse
min(previous S, max(1 day, S × 0.3))) was removed on 2026-11-16 and is
retrievable at commit `b854419`. It remains the hidden memory of the
historical 2026-11-13 experiment; the two subsections below describe it for
reading that experiment.

Recall follows section 3.2's power-law curve. State is per client and line:
stability, difficulty, familiarity, last session time, last-review lapse and
session count. Guided Learning updates hidden memory too, with its
latency-derived grade. A client built without sampled weights gets the
FSRS-6 defaults with w20 = its C (`FSRSMemory.default`).
`LineMemory.elapsed` rejects time going backwards.

FSRS hidden weights start at defaults with log-normal noise (sd 0.15) on
w0–w16; w17–w19 stay at defaults, w0–w3 are sorted, and w20 is assigned the
client's C before all weights are clipped to FSRS bounds. Weights have a
separate random stream, preserving client/side/repertoire draws when the
memory setting changes. For C outside the model's w20 range 0.1–0.8, the
exported hidden weight vector contains a clipped w20 while recall still
uses the trait's C. The current `FSRSMemory.start/update` functions do not
read w20: update receives the recall R computed by the client from trait C.
Clipping that exported coefficient therefore does not change the current
hidden simulation. The exported vector's forgetting curve and the fitter's
bounded decay may not represent that trait-C recall curve outside the range.
This source-derived representability limit was not measured in the historical
populations.

### How the two updates differ

Historical: the multiplicative model was removed on 2026-11-16.

Until 2026-11-16, with the earlier grading rule, everything except the
stability update was shared: the recall curve and per-move draws
(clean-session chance R^M), latency, grading, retries and the collection
policy. With the same seed and catalog the clients, sides and
repertoires are identical (2026-11-14 experiment). The two update rules, read
from `memory/multiplicative.py` and `fsrs/model.py` (`recall_stability`,
`forget_stability`, `next_difficulty`):

| Question | Multiplicative | FSRS hidden memory |
|---|---|---|
| What sets the growth after a clean session? | R only: the factor 1 + 1.5·exp(2(1−R)) | Grade, difficulty D, current S and R: S·(1 + e^w8·(11 − D)·S^(−w9)·(e^(w10(1−R)) − 1)·hard·easy) |
| Does the grade (Hard, Good, Easy) matter? | No; any clean session counts the same | Yes; w15 scales Hard and w16 scales Easy, and the FSRS bounds keep w15 ≤ 1 ≤ w16, so Easy grows memory most and Hard least |
| Does a line keep a difficulty? | No | Yes; D moves with every grade (Again raises it), and growth shrinks as D rises toward its maximum of 10 |
| Does growth shrink for strong memories? | No; the factor does not depend on S | Yes, through S^(−w9) |
| What happens after a lapse? | S × 0.3 | Forget update; both use the same lapse clamp |
| Are the parameters per client? | Shared constants; clients differ in C | Each client's own sampled 21 weights |

Arithmetic from the multiplicative formula: the factor is 2.83 at R = 0.9 and
5.08 at R = 0.5. Observed pass rates of tested reviews on test clients:
58.2% with multiplicative memory (2026-11-13 experiment, 91 families) and
38.4% with FSRS memory (2026-11-14 experiment, 82 families). Which rule
difference causes the lower FSRS-memory pass rate was not measured, and the
catalog grouping also differed.

### Worked example: one review under both rules

Historical: the multiplicative model was removed on 2026-11-16, and the
pass chance R^6 below is the earlier no-mistake rule.

Computed on 2026-11-16 with the package's own update functions
(`MultiplicativeStability.after_success/after_lapse` and
`FSRSMemory.start/update`), not a simulation run. Setup: a balanced client
(C = 0.5), a 6-move line with stability S = 4 days, reviewed after t days.
FSRS memory uses the FSRS-6 default weights with w20 = C; a real client's
own weights are sampled around these (±15% log-normal noise), so its
numbers differ somewhat. R is per-move recall; the line passes with
chance R^6.

| Review | R | Pass chance | Multiplicative: new S | FSRS memory: new S | FSRS: new D (from 5) |
|---|---|---|---|---|---|
| On time (t = 4), clean, Good, D = 5 | 0.900 | 53% | 11.3 d (×2.83) | 14.3 d (×3.57) | 4.99 |
| On time, clean, Hard, D = 5 | 0.900 | 53% | 11.3 d (×2.83) | 10.2 d (×2.54) | 6.67 |
| On time, clean, Easy, D = 5 | 0.900 | 53% | 11.3 d (×2.83) | 23.2 d (×5.81) | 3.31 |
| On time, clean, Good, hard line D = 9 | 0.900 | 53% | 11.3 d (×2.83) | 7.4 d (×1.86) | 8.99 (from 9) |
| Late (t = 8), clean, Good, D = 5 | 0.825 | 32% | 12.5 d (×3.13) | 22.5 d (×5.63) | 4.99 |
| On time, mistake (Again), D = 5 | 0.900 | 53% | 1.2 d (×0.30) | 1.0 d (one-day floor) | 8.34 |
| Strong line S = 40, on time, Good, D = 5 | 0.900 | 53% | 113.3 d (×2.83) | 109.9 d (×2.75) | 4.99 |

First exposure: multiplicative memory always starts at S = 1 day; FSRS
memory starts from the first grade, at S = 0.21 / 1.29 / 2.31 / 8.30 days
and D = 6.41 / 5.11 / 2.12 / 1.00 for Again / Hard / Good / Easy.

Reading the table: multiplicative memory gives every clean on-time review
the same ×2.83, whatever the grade, the line's history or its strength.
FSRS memory gives Easy more than twice the growth of Hard, grows a hard
line (D = 9) less than half as fast, rewards a late but clean review more
(×5.63 against ×3.13), and after a mistake also raises D, so the next clean
reviews grow less. For a strong line its factor falls slightly below the
multiplicative one, through S^(−w9).

The byte-identity check in the 2026-11-14 experiment found the multiplicative
generator unchanged when FSRS memory was added, on the same catalog. This
is historical evidence, not a fresh run. The published A2/B2 and A1/A1c/B1
studies used different catalog groupings (91 versus 82 families), so their
results do not isolate the hidden-memory change alone.

## 8. Simulator, app and accepted specification

The offline producer uses grade-based noisy intervals and, since
2026-11-16, the decided grading rule without a baseline. The app uses py-fsrs
scheduling, persisted move events with browser-measured times and, since
`52e9535`, the decided rule. Its runtime
selection/storage boundary belongs to [App & practice](../app-practice/app-practice.md).

The package grades guided sessions, updates hidden memory, then tests after
the guided duration plus three minutes. In the app, finishing Learning
initializes a due card without grading or initializing stability; the first
Repeating session does that (`backend/ml_controller.py`,
`initialize_progress`, `complete_review`). The package samples eligible
catalog lines with unique names within a repertoire; the app admits only
lines no other catalog line extends. The package caps attempts at five;
the app supports retries and explicitly stopped reviews. These implemented
differences do not amend the accepted product requirements. Their effect on
transfer to human app practice has not been measured.

Hidden FSRS memory is not an exact unmodified FSRS process: its stability
update has a lapse floor and the whole session's grade, while the chance
of passing a line is `p_pass(R, M)`. Whether it resembles human players
remains open; Stage 2 calibration is future work.

## 9. Practice policy, generation and demo producer

### Offline collection policy

`SyntheticClient` answers what happens when a specified player practises a
specified line at a simulation day. `ClientPlan` and `simulate_client`
choose the time and line. Memory uses `line_id`; `_pick_repertoire` rejects
duplicate display names per client so the seven-column export can key cards
by `(agent_name, opening_name)`.

`catalog.load_opening_lines` opens SQLite read-only, joins lines/families,
orders by `line_id`, and derives side-specific move counts as
`(plies + 1) // 2` and `plies // 2`. A line must have the player's family
side and the configured minimum move count. It does not apply the app's
leaf-line rule. [Catalog & data](../catalog-data/catalog-data.md) owns tables,
catalog provenance and app learnability.

The four `ml/configs/*memory*.json` files configure the following values,
which are synthetic settings, not measured human traits:

| Setting | Main / hold-out value |
|---|---|
| Seed; clients per each of three archetypes | 20261111 / 20261112; 100 / 20 |
| Horizon | 180 days |
| Requested repertoire; families initially sought | 15–40 lines; 2–6 families |
| Minimum repertoire moves from player's side | 2 |
| New lines per active day; fixed per-client review budget | 1–3; sampled 8–30 |
| Per-client active-day probability | Uniform 0.50–0.95 |
| Interval noise sigma; interval cap | 0.35; 365 days |
| Trait standard deviations: baseline, mu, sigma, beta, alpha, C | 25 ms, 0.15, 0.05, 0.2, 0.04, 0.05 |
| Memory | multiplicative by default; FSRS configs set `memory = fsrs` |

Families are permuted uniformly. The pool may extend beyond the sampled
family count to get enough lines; name deduplication or a small pool may
leave the repertoire below the requested size. Active days begin uniformly
between 0.3 and 0.7 days. Lines due before that day's end are sorted oldest
first and capped by the client's budget; new lines follow. Recorded session
duration advances the clock, with one-minute ordinary gaps and three
minutes after guided Learning before its immediate unassisted test.

Again resets the base interval to one day. Hard/Good/Easy multiply the
previous interval by 1.2/2.5/3.5, with minimum base intervals of one day for
Hard/Good and two for Easy. Log-normal noise then applies, followed by the
configured cap. This is a data-collection policy, not FSRS scheduling.

`build_plans` separates client, policy and weight random streams; `generate`
uses scheduling seeds derived from `[seed, 1]`. `build_population` is an
in-memory alternative with exact archetypes unless supplied distributions;
the CLI uses `build_plans` with bounded trait spread. The manifest records
config/model/retry cap, counts, ordered catalog-content identity, CSV hashes,
Python/NumPy/platform, source commit when available, and generation seconds.
Its catalog hash excludes mutable practice history. A commit alone cannot
capture uncommitted producing changes; reproduction needs the experiment's
pin, diff and input identities. [Review Dataset](../review-dataset/record.md#5-generated-files-and-producer-boundaries)
owns output fields and sidecar alignment.

### Backend demo producer

`backend/synthetic_clients.py` is separate from this package. `Profile`
uses the same three cognitive profiles, but `generate_dataset` uses Python
`Random(seed)` and a default py-fsrs `Scheduler(enable_fuzzing=False)`,
rather than the runtime weights or package collection policy.
`simulate_line` counts **all UCI plies**, starts on 2026-01-01 UTC with status
`new` and R = 1, then emits `review` or `relearning`. Each failed first
attempt gets exactly one successful retry, with retry latency sampled at
R = 1. Due dates come from `MLEngine`; attendance varies by 0.5–2 times the
due delay, with a one-second minimum. Familiarity follows +1 / minus 2.

Default demo lines are Sicilian Defence and Italian Game. An optional
read-only catalog input can select the first line per family; duplicate
names gain `[line ID]`. An atomic CSV write replaces the output only after
writing all rows. These rows have no package truth sidecars or manifest;
they are demo telemetry, not either package study or human calibration.
[ML development](../../development/ml.md) owns CLI usage.

## 10. Source coverage and verification limits

The bounded 2026-11-15 source pass at
`788e06039dd2869b23261dd80ea8fc49367ab33c` read every `ml/tempo_ml/` file,
all four generator configs, `ml/pyproject.toml`, four ML test files and the
backend demo producer. It filled scattered memory-model, policy, random-stream,
config and producer-boundary documentation. Schema and fitting remain in
their own records; no additional ML topic is needed for the inspected package.

| Source / symbols | Canonical section or owner |
|---|---|
| `simulator/clients.py`: `ClientTraits`, `TraitDistribution`, `Line`, `SyntheticClient`, `build_population` | Sections 3–4, 6–9 |
| `simulator/recall.py`: `MoveEvent`, `sample_move_time_ms`, `play_move` | Sections 3.3–3.4 and 6 retry discrepancy |
| `simulator/memory/state.py`: `LineMemory`, `retrievability`, `next_reps` (2026-11-16; before, in the removed `memory/multiplicative.py` with `StabilityModel` and `MultiplicativeStability`) | Sections 3.2, 3.5 and 7 |
| `simulator/memory/fsrs.py`: `FSRSMemory.default`, `sample`, `start`, `update` | Section 7; FSRS Training owns fitting formulas |
| `simulator/practice.py`: `GenerationConfig`, `_pick_repertoire`, `build_plans`, `_next_interval`, `simulate_client` | Section 9 |
| `simulator/generate.py`: `generate`, `load_config`, `main`, `_catalog_sha256` | Section 9; Review Dataset owns files; ML development owns commands |
| `catalog.py`: `OpeningLine`, `load_opening_lines` | Section 9 consumer contract; Catalog & data owns source tables |
| `backend/synthetic_clients.py`: `Profile`, `simulate_line`, `generate_dataset`, `read_lines`, `write_dataset`, `main` | Section 9 |
| Package/simulator/memory `__init__.py` files | Exports and package scope; app runtime planner is separate |
| `ml/configs/*.json`; `test_simulator.py`, `test_memory_models.py` | Sections 4, 7 and 9; inspected formula/trait/state/catalog/deterministic generation/hidden-model assertions |

Verified implementation facts come from source inspection. Tests were read,
not executed. They bound attempt counts without proving the final attempt
successful, so the retry discrepancy remains. No generation, training,
benchmark, app session or human experiment was run. Historical numeric and
byte-identity results retain their original evidence scope.

## Page presentation and numeric sources

The authored page presents memory and recall before latency, followed by the
benchmark profiles. Its existing public section and figure anchors remain.
Inline diagrams are source-authored in `index.md`: the memory diagram uses
sections 3.2, 3.3, 3.5 and 6; the latency diagram uses section 3.4. They show
model construction, not human measurements.

| Displayed numbers or construction | Canonical source |
|---|---|
| R at 0 and 1; S at 90% recall; calibration factor 0.9; clean chance R^M | Sections 3.2, 3.3 and 6 |
| Milliseconds conversion 1000; practice multiplier 1/(1 + alpha n); familiarity +1 / minus 2 with floor 0 | Sections 3.4 and 3.5 |
| Guided R = 1; test after three minutes; five-attempt cap | Section 6 |
| Hidden-memory growth ×2.83 at R = 0.9 and ×5.08 at R = 0.5; lapse ×0.3 with one-day floor; 21 sampled FSRS weights | Section 7 |
| Pass rates 58.2% (multiplicative) and 38.4% (FSRS memory); 91 versus 82 families | Section 7, from the 2026-11-13 and 2026-11-14 experiment records |
| Worked example: C = 0.5, 6 moves, S = 4 and 40 days, t = 4 and 8, D = 5 and 9; resulting R, pass chances, new S, factors and D; first-exposure S and D per grade | Section 7, worked example; computed with the package's update functions and FSRS-6 default weights, not a simulation result |
| Profile baselines 220/300/380 ms; beta 0.4/1.0/2.2; C 0.65/0.50/0.35 | Section 4 |

These are formula constants and configured/modelled values, not measured
human results; the two pass rates are synthetic experiment measurements. Figure and chapter numbers are presentation identifiers.
