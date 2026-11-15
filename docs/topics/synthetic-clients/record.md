# Topic Record: Synthetic Client Behavioral & Cognitive Model

## 1. Scope & Ownership

| Item | Canonical Owner |
|---|---|
| Technical specification & parameters | `docs/topics/synthetic-clients/record.md` |
| Human-facing documentation & explanation | `docs/topics/synthetic-clients/index.md` |
| Project context & product vocabulary | `docs/PROJECT_CONTEXT.md` |
| Review session dataset & grading function | `docs/topics/review-dataset/record.md` (Topic 2) |

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

$$\text{reps}_{k+1} = \begin{cases} \text{reps}_k + 1 & \text{if session completed without blunder} \\ \max(0, \text{reps}_k - 2) & \text{if a blunder occurred} \end{cases}$$

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
the data-collection policy. The [FSRS training record](../fsrs-training/fsrs-training.md)
owns hidden stability updates, training, recorded experiments and differences
from the app's runtime engine.

- Every repertoire move has an independent first-attempt recall draw with
  the same line-level R. A clean session therefore has probability R^M,
  where M is the number of the player's moves. Hidden stability and
  familiarity remain per line, not separate states for each move.
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
  The [review dataset record](../review-dataset/record.md) owns those fields.
- Archetype values are benchmark settings, not fitted human cohorts.
  `TraitDistribution` supplies bounded multivariate-normal sampling as a
  calibration hook; no parameter-estimation or human-fit validation pipeline
  is implemented in `ml/tempo_ml/`.

The separate `backend/synthetic_clients.py` is a demo telemetry generator,
not this package: it counts all plies, uses the backend scheduler and one
successful retry after a failed first attempt. Do not treat its output as
one of the package experiment datasets or as a validated human calibration.

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
| Profile baselines 220/300/380 ms; beta 0.4/1.0/2.2; C 0.65/0.50/0.35 | Section 4 |

These are formula constants and configured/modelled values, not measured
human results. Figure and chapter numbers are presentation identifiers.
