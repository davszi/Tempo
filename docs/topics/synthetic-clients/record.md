# Topic Record: Synthetic Client Behavioral & Cognitive Model

## 1. Scope & Ownership

| Item | Canonical Owner |
|---|---|
| Technical specification & parameters | `docs/topics/synthetic-clients/record.md` |
| Human-facing documentation & explanation | `docs/topics/synthetic-clients/index.md` |
| Project context & product vocabulary | `docs/PROJECT_CONTEXT.md` |
| Review session dataset & grading function | `docs/topics/review-dataset/record.md` (Topic 2) |

This record specifies the behavioral, cognitive, and latency simulation engine for **Synthetic Clients** in TEMPO. Synthetic clients generate simulated practice histories (repetitions, move accuracy, and move hesitation times) across opening lines to train and calibrate the Review Planner and FSRS without cold-start dependencies on human user data.

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
- $\mu \in \mathbb{R}$: Median parameter of the raw cognitive hesitation log-normal distribution.
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
