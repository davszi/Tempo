+++
toc = []
title = "Synthetic players"
slug = "synthetic-clients"
description = "See how simulated players turn memory and timing assumptions into practice attempts."
brand_sub = "cognitive modeling · spaced repetition · latency generation"
components = ["toc", "nav", "code", "filelinks"]
page_css = ["build-sheet.css"]
math = true
+++

# Synthetic players

<section class="card" id="overview">

<span id="synthetic-clients-simulating-human-opening-review"></span>

## 1. Overview & Purpose

<p class="bs-lead">Synthetic clients generate practice histories under explicit memory and timing assumptions; they have not been calibrated against human players.</p>

The `tempo_ml` package uses simulated players to study training before human data is available. Its [synthetic-client record](docs.topics.synthetic-clients.record.md.html#6-implementation-and-open-choices) distinguishes implemented policy from the demo specification. Each attempt produces two signals:
- **Move Accuracy:** Did the client recall the exact repertoire move?
- **Hesitation Latency:** How many milliseconds did the client spend searching their memory or calculating?

The separate `backend/synthetic_clients.py` generator produces demo telemetry. Its all-ply counting and successful-retry policy differ from the package simulator; the datasets are not interchangeable.

</section>

<section class="card" id="memory-dynamics">

<span id="3-memory--lapse-dynamics"></span>

## 2. Memory & Lapse Dynamics

<p class="bs-lead">Retrievability sets each attempt's recall probability; the model reduces familiarity after a lapse.</p>

<figure id="fig-memory">
<div class="bs-flow" role="img" aria-label="Elapsed time and line stability determine recall probability. Each repertoire move draws independently; a first-attempt error makes the session a lapse and reduces familiarity.">
<div class="bs-node bs-violet"><span class="bs-label">Line memory</span><b>Time and stability</b><p>The forgetting curve gives retrievability R.</p></div>
<div class="bs-arrow"><span>recall draw</span></div>
<div class="bs-node bs-orange"><span class="bs-label">Move attempts</span><b>Correct or retry</b><p>A clean line requires every independent first attempt to succeed.</p></div>
<div class="bs-arrow"><span>update</span></div>
<div class="bs-node bs-teal"><span class="bs-label">After the session</span><b>Familiarity changes</b><p>Clean reviews add familiarity; a lapse reduces it. The selected memory model also updates stability.</p></div>
</div>
<figcaption><strong>Figure 1.</strong> Source-authored construction from the <a href="docs.topics.synthetic-clients.record.md.html#6-implementation-and-open-choices">implemented synthetic-client model</a>. Arrows show computation and state updates.</figcaption>
</figure>

[Figure 1](#fig-memory) separates line-level memory from independent move attempts. Longer lines offer more opportunities for a first-attempt error even when per-move recall is identical.


### Retrievability Formula
Retrievability $R(t, S)$ follows the modern FSRS power-law forgetting curve:

$$R(t, S) = \left(1 + F \cdot \frac{t}{S}\right)^{-C}$$

- **$t$:** Days elapsed since last review.
- **$S$:** Line memory stability (days until $R = 0.9$).
- **$C$:** Client forgetting power (trait).
- **$F$:** Scaling factor ($0.9^{-1/C} - 1$).

### Decision Rule
$$\text{Move Accuracy} = \begin{cases} \text{Repertoire Move} & \text{with probability } R \\ \text{Blunder / Mistake} & \text{with probability } 1 - R \end{cases}$$

### Lapse State Transitions
In TEMPO Repeating Mode, mistakes are immediately retracted rather than played out. When a client blunders on a previously learned line:

$$\text{reps}_{k+1} = \begin{cases} \text{reps}_k + 1 & \text{if clean review (success)} \\ \max(0, \text{reps}_k - 2) & \text{if blunder occurs (soft penalty)} \end{cases}$$

This soft penalty is a modeling choice: it retains some accumulated familiarity. It is not an established psychological result.

In the package, each of the player's $M$ moves has an independent first-attempt draw with the same line-level $R$. A clean session therefore has probability $p_{\mathrm{clean}} = R^M$. Memory stability and familiarity remain per line. Guided sessions instead use perfect accuracy and $R=1$ latency, update hidden memory, and are followed by an unassisted test after the session duration plus three minutes.

The current implementation caps attempts at five. If the last draw fails, the session still advances without representing a successful final attempt. This unresolved behavior differs from the stated retry assumption; see [implementation limits](docs.topics.synthetic-clients.record.md.html#6-implementation-and-open-choices).

</section>

<section class="card" id="hesitation-model">

<span id="2-the-hesitation-latency-engine"></span>

## 3. The Hesitation Latency Engine

<p class="bs-lead">Reaction time is not uniform: it combines physical interface latency, log-normal cognitive delay, and exponential strain from memory decay.</p>

[Figure 2](#fig-latency) separates sampled hesitation from the memory and practice factors that scale it. The baseline is added after those factors; effort changes latency without directly changing recall probability.

<figure id="fig-latency">
<div class="bs-flow" role="img" aria-label="A log-normal hesitation draw in seconds is converted to milliseconds, multiplied by memory strain and practice fluency, then added to the physical baseline.">
<div class="bs-node bs-violet"><span class="bs-label">Sample</span><b>Raw hesitation</b><p>Log-normal draw in seconds</p></div>
<div class="bs-arrow"><span>scale</span></div>
<div class="bs-node bs-orange"><span class="bs-label">Multiply</span><b>Strain and practice</b><p>Lower retrievability raises strain; familiarity reduces delay.</p></div>
<div class="bs-arrow"><span>add baseline</span></div>
<div class="bs-node bs-teal"><span class="bs-label">Attempt</span><b>Total latency</b><p>Physical baseline plus scaled cognitive hesitation</p></div>
</div>
<figcaption><strong>Figure 2.</strong> Source-authored diagram of the <a href="docs.topics.synthetic-clients.record.md.html#34-hesitation-latency-model">latency model</a>; it shows assumptions, not measured human reaction times.</figcaption>
</figure>

$$T_{\mathrm{ms}} = b_{\mathrm{ms}} + 1000 H \exp\bigl(\beta(1-R)\bigr)\frac{1}{1+\alpha n}, \qquad H\sim\operatorname{Lognormal}(\mu,\sigma)$$

Here $T_{\mathrm{ms}}$ is attempt latency, $b_{\mathrm{ms}}$ the physical baseline, $H$ raw hesitation in seconds, $R$ retrievability and $n$ accumulated familiarity. The factor 1000 converts seconds to milliseconds. The [model record](docs.topics.synthetic-clients.record.md.html#34-hesitation-latency-model) defines the same construction in full.

### Cognitive Components:

1. **Physical Baseline ($\text{baseline\_ms}$):**
   An assumed floor for motor, visual-processing and interface delay; it is a client parameter rather than a measured physiological limit.
2. **Raw Cognitive Hesitation ($\mu, \sigma$):**
   A log-normal draw gives a right-skewed distribution. The parameter $\mu$ is the mean of log(seconds), so its median in seconds is $e^\mu$; $\sigma$ controls dispersion. Human agreement remains unmeasured.
3. **Cognitive Strain ($\beta$ and $R$):**
   When an opening line is fresh in memory ($R \approx 1.0$), retrieval is effortless ($\text{strain} \to 1.0$). When retrievability drops, the client spends cognitive effort $\beta$ struggling to remember or calculate.
4. **Practice Decay ($m_{\text{practice}}$ and $\alpha$):**
   With each review, the line becomes more automatic. As repetitions grow, $m_{\text{practice}} \to 0$, causing hesitation to approach pure physical baseline.

</section>

<section class="card" id="archetypes">

## 4. Benchmark Personas for Demo

<p class="bs-lead">Three benchmark profiles vary the simulator's timing and forgetting parameters; they are not fitted human cohorts.</p>

<div class="bs-grid g3">
    <div class="bs-part bs-muted">
      <h4>The Impulsive Blitzer</h4>
      <p>Low baseline (220 ms), low effort (\(\beta = 0.4\)), fast decay (\(C = 0.65\)). Moves fast, hesitates little even when uncertain, but blunders when lines are neglected.</p>
    </div>
    <div class="bs-part bs-teal">
      <h4>The Balanced Learner</h4>
      <p>Standard baseline (300 ms), moderate effort (\(\beta = 1.0\)), average decay (\(C = 0.50\)). A benchmark reference profile, not a measured average player.</p>
    </div>
    <div class="bs-part bs-muted">
      <h4>The Diligent Calculator</h4>
      <p>High baseline (380 ms), high effort (\(\beta = 2.2\)), strong retention (\(C = 0.35\)). Takes significant time when retention dips, building high automaticity through practice.</p>
    </div>
</div>

The [benchmark profile table](docs.topics.synthetic-clients.record.md.html#4-benchmark-archetypes-stage-1-demo-profiles) gives the remaining parameters. Position depth and sharpness multipliers remain [future extensions](docs.topics.synthetic-clients.record.md.html#5-deferred-context-extensions-post-demo-scope).

</section>
