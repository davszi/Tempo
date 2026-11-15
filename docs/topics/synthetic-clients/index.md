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

## Simulated practice exposes the assumptions before human data exists

<p class="bs-lead">Synthetic clients generate practice histories under explicit memory and timing assumptions; they have not been calibrated against human players.</p>

The `tempo_ml` package uses simulated players to study training before human data is available. Its [synthetic-client record](docs.topics.synthetic-clients.record.md.html#6-implementation-and-open-choices) distinguishes implemented policy from the demo specification. Each attempt produces two signals:

<div class="scroll" role="region" aria-label="Synthetic signals; scroll horizontally on narrow screens" tabindex="0" data-reader-horizontal style="overflow-x:auto">
<div style="min-width:600px">

| Signal | Modelled meaning | Boundary |
|---|---|---|
| Move accuracy | Did the recall draw produce the exact repertoire move? | Correctness does not grade the chess quality of an alternative move. |
| Hesitation latency | Physical baseline plus sampled, scaled cognitive delay. | These timings are generated assumptions, not measurements of human thought. |

</div>
</div>


The simulator separates a player's response from the collection policy that chooses when and what to practise. Its memory state is hidden; exported session summaries are the observable training input.

The separate `backend/synthetic_clients.py` generator produces demo telemetry. Its all-ply counting and successful-retry policy differ from the package simulator; the datasets are not interchangeable.

</section>

<section class="card" id="memory-dynamics">

<span id="3-memory--lapse-dynamics"></span>

## One line memory supplies independent move-recall draws

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


<section class="card" id="hidden-memory">

## Two hidden memory models update the same per-line state

<p class="bs-lead">Both models supply the same recall curve, but their stability updates make different synthetic populations.</p>

<figure id="fig-hidden-models">
<div class="bs-flow">
<div class="bs-node"><b>Shared inputs</b><small>Line state, elapsed simulation days and the session outcome enter the configured memory model.</small></div>
<div class="bs-arrow"><span>choose model</span></div>
<div class="bs-stack"><div class="bs-part"><h3>Multiplicative</h3><p>Start at one day; clean recall multiplies stability, while a lapse reduces it with a floor.</p></div><div class="bs-part"><h3>FSRS hidden memory</h3><p>Grade initializes stability/difficulty; later updates use short-term or recall/forget equations plus a lapse clamp.</p></div></div>
<div class="bs-arrow"><span>save state</span></div>
<div class="bs-node"><b>Next recall curve</b><small>Updated stability, familiarity and last-session time determine the next simulated session.</small></div>
</div>
<figcaption><strong>Figure 2.</strong> Arrows show alternative update paths, not two fits run inside the app. Generator: this page's HTML; input: <a href="docs.topics.synthetic-clients.record.md.html#7-offline-simulator-and-hidden-memory">hidden-model implementation</a>.</figcaption>
</figure>

<a href="#fig-hidden-models">Figure 2</a> locates the choice behind the shared retrievability formula. Stability, familiarity, last session time, lapse state and session count belong to a client/line; FSRS memory also keeps difficulty. Time cannot run backwards.

<div class="scroll" role="region" aria-label="Hidden memory models; scroll horizontally on narrow screens" tabindex="0" data-reader-horizontal style="overflow-x:auto">
<div style="min-width:640px">

| Model | First exposure | Later update |
|---|---|---|
| Multiplicative | Stability starts at one day. | A clean session multiplies stability by a recall-dependent factor. A lapse takes the smaller of previous stability and its reduced value with a one-day floor. |
| FSRS hidden memory | The first grade initializes stability and difficulty. | Below one elapsed day it uses short-term stability; later it uses recall/forget updates. A lapse clamps the result to the smaller of previous stability and its updated value with a one-day floor. |

</div>
</div>


Guided Learning updates hidden memory too: multiplicative memory treats it as success; FSRS memory uses its latency-derived grade. FSRS hidden weights are sampled around defaults in a separate random stream, then constrained to allowed bounds. The exported decay coefficient can be clipped while hidden recall and updates still use the client's original trait through R. This limits what the exported vector or bounded fitter can represent outside that range; the <a href="docs.topics.synthetic-clients.record.md.html#7-offline-simulator-and-hidden-memory">record</a> explains the boundary.

Neither model is an exact ordinary app scheduler. FSRS hidden memory adds the lapse clamp and a session-level grade, while the clean-session chance remains <code>R^M</code>. Multiplicative memory is a separate construction. Which resembles human players remains unknown. The dated studies also changed catalog grouping, so their results do not isolate the memory-model change alone.

</section>

<section class="card" id="hesitation-model">

<span id="2-the-hesitation-latency-engine"></span>

## Latency adds a baseline to memory-dependent hesitation

<p class="bs-lead">Reaction time is not uniform: it combines physical interface latency, log-normal cognitive delay, and exponential strain from memory decay.</p>

[Figure 3](#fig-latency) separates sampled hesitation from the memory and practice factors that scale it. The baseline is added after those factors; effort changes latency without directly changing recall probability.

<figure id="fig-latency">
<div class="bs-flow" role="img" aria-label="A log-normal hesitation draw in seconds is converted to milliseconds, multiplied by memory strain and practice fluency, then added to the physical baseline.">
<div class="bs-node bs-violet"><span class="bs-label">Sample</span><b>Raw hesitation</b><p>Log-normal draw in seconds</p></div>
<div class="bs-arrow"><span>scale</span></div>
<div class="bs-node bs-orange"><span class="bs-label">Multiply</span><b>Strain and practice</b><p>Lower retrievability raises strain; familiarity reduces delay.</p></div>
<div class="bs-arrow"><span>add baseline</span></div>
<div class="bs-node bs-teal"><span class="bs-label">Attempt</span><b>Total latency</b><p>Physical baseline plus scaled cognitive hesitation</p></div>
</div>
<figcaption><strong>Figure 3.</strong> Source-authored diagram of the <a href="docs.topics.synthetic-clients.record.md.html#34-hesitation-latency-model">latency model</a>; it shows assumptions, not measured human reaction times.</figcaption>
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

## Benchmark profiles vary traits; they are not human cohorts

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

<section class="card" id="collection-policy">

## The collection policy chooses attendance, lines and the next interval

<p class="bs-lead">A synthetic client's response model does not decide the practice schedule; a separate policy generates the history presented to the fitter.</p>

<figure id="fig-collection">
<div class="bs-flow">
<div class="bs-node"><span class="bs-label">Configuration & catalog</span><b>Build client plans</b><small>Sample traits, side, repertoire and attendance/budget. Catalog reads are read-only.</small></div>
<div class="bs-arrow"><span>active day</span></div>
<div class="bs-node"><span class="bs-label">Collection policy</span><b>Review then learn</b><small>Oldest due lines use the budget; new lines follow. Guided Learning gets an immediate later unassisted test.</small></div>
<div class="bs-arrow"><span>advance</span></div>
<div class="bs-node"><span class="bs-label">Response & grade</span><b>Set next interval</b><small>Grade-based interval factors plus noise decide future collection. Session duration and gaps advance simulation time.</small></div>
</div>
<figcaption><strong>Figure 4.</strong> Arrows mean synthetic collection order. This interval policy is not Py-FSRS scheduling. Generator: this page's HTML; input: <a href="docs.topics.synthetic-clients.record.md.html#9-practice-policy-generation-and-demo-producer">practice policy and generation</a>.</figcaption>
</figure>

<a href="#fig-collection">Figure 4</a> separates <code>SyntheticClient</code>, which answers how a player responds, from the plan that chooses a time and line. Repertoires select the player's family side and a minimum move count. They can include headings that the app would refuse for new Learning, but they reject duplicate display names within a client to protect the CSV card key. Memory itself uses line IDs.

Again resets the base interval; other grades multiply it. Interval noise and a cap then apply. Guided sessions use perfect accuracy and are followed by a test after their duration plus three minutes. The <a href="docs.topics.synthetic-clients.record.md.html#9-practice-policy-generation-and-demo-producer">configuration table and exact factors</a> give the synthetic horizon, budgets, trait spread, random streams and interval rules.

<div class="scroll" role="region" aria-label="Synthetic producer comparison; scroll horizontally on narrow screens" tabindex="0" data-reader-horizontal style="overflow-x:auto">
<div style="min-width:680px">

| Producer | Move unit and retries | Scheduling and outputs |
|---|---|---|
| Maintained offline package | Player-side repertoire moves; attempts are capped, with unresolved final-failure semantics. | Grade/noise collection policy; observable sessions plus hidden truth, client/repertoire sidecars and a manifest. |
| Backend demo generator | All UCI plies; a failed first attempt receives one successful retry. | Backend scheduler with fuzzing disabled; the session CSV has no package truth sidecars or manifest. |
| Current app | Persisted player move attempts and explicitly closed reviews. | Runtime Py-FSRS card scheduling; Learning initializes a due card without graded hidden-memory learning. |

</div>
</div>


The shared CSV header does not make those datasets interchangeable. <a href="review-dataset.html#generated-files">Review Data & Grading</a> explains observable versus hidden output, and <a href="docs.development.ml.md.html">ML development</a> supplies the supported setup and CLI commands. Generating data, fitting weights and evaluating results are separate commands; none runs inside the browser's review request.

The manifest retains config/model, retry cap, ordered catalog-content identity, output hashes, source and environment. Exact reproduction also needs producing changes absent from a commit alone. This page explains the source audit at <code>788e060</code>; no new generation, tests, training or human calibration were run. <a href="docs.topics.synthetic-clients.record.md.html#10-source-coverage-and-verification-limits">Verification limits</a> distinguish inspected tests from executed historical evidence.

</section>
