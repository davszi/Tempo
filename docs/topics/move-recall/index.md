+++
toc = []
title = "Move recall"
slug = "move-recall"
description = "Follow why FSRS recall now means one move, how the pass chance of a line is computed from it, and how the two new training targets compare with the earlier arms."
brand_sub = "per-move recall · pass chance · accuracy target"
components = ["toc", "nav", "code", "filelinks"]
page_css = ["build-sheet.css"]
math = true
+++

# Move recall

<section class="card" id="meaning">

## FSRS recall now means one move, and the line's pass chance is computed from it

<p class="bs-lead">FSRS predicts the chance of getting one move of a line right. The chance of passing the whole line under the session grading rule is calculated from that and the line's length. A line is due when that pass chance falls to 90%. Decided on 2026-11-16, not implemented yet.</p>

<div class="bs-checks">
<div class="bs-check"><span class="bs-badge bs-ok">Decided</span><h3>Decided on 2026-11-16</h3><p>Per-move recall, a 0.9 pass-chance target and four training arms.</p></div>
<div class="bs-check"><span class="bs-badge bs-ok">Implemented in ML</span><h3>Simulator, training and scoring use per-move recall</h3><p>The app grades with the new rule, but still schedules reviews on line-level recall.</p></div>
<div class="bs-check"><span class="bs-badge bs-ok">Trained</span><h3>Retrained on 2026-11-16</h3><p>Both new training targets were trained side by side in the move-recall experiment.</p></div>
</div>

<figure id="fig-meaning">
<div class="bs-flow" role="img" aria-label="FSRS gives the per-move recall R of a line. Together with the number of moves M and the line's mistake limit, the binomial formula gives the pass chance of the line. The scheduler makes the line due when the pass chance falls to 0.9.">
<div class="bs-node bs-violet"><span class="bs-label">FSRS</span><b>Per-move recall R</b><p>The chance of getting one move of the line right on the first attempt.</p></div>
<div class="bs-arrow"><span>line length</span></div>
<div class="bs-node bs-orange"><span class="bs-label">Pass chance</span><b>p_pass(R, M)</b><p>The chance of at most the line's mistake limit of mistakes.</p></div>
<div class="bs-arrow"><span>schedule</span></div>
<div class="bs-node bs-teal"><span class="bs-label">Scheduler</span><b>Due at 0.9</b><p>The line is due when its pass chance falls to 90%.</p></div>
</div>
<figcaption><strong>Figure 1.</strong> How the <a href="docs.topics.move-recall.move-recall.md.html#3-decisions">decided model</a> turns per-move recall into a due date. Arrows show the order of the calculation, not code that runs today. Generator: this page's HTML.</figcaption>
</figure>

**The pass chance.** A line of $M$ moves passes when it has at most $L(M)$ mistakes, the limit from the [session grading rule](session-grading.html). If each move is right with chance $R$, independently:

$$p_\text{pass}(R, M) = \sum_{k=0}^{L(M)} \binom{M}{k} (1-R)^k R^{M-k}$$

Worked once: a 6-move line may have one mistake. At $R = 0.9$, no mistake has chance $0.9^6 = 0.531$ and exactly one mistake $6 \cdot 0.9^5 \cdot 0.1 = 0.354$, so the pass chance is $0.886$.

**The scheduling target.** Because the limit depends only on the length, the per-move recall at which the pass chance is exactly 0.9 is one fixed number per line length, $R^*(M)$. Short lines allow no mistake, so they need high per-move recall; longer lines allow some:

<div class="scroll" role="region" aria-label="Per-move target by line length; scroll horizontally on narrow screens" tabindex="0" data-reader-horizontal style="overflow-x:auto">
<div style="min-width:520px">

| Moves in the line | 3 | 6 | 10 | 14 |
|---|---|---|---|---|
| Mistake limit $L(M)$ | 0 | 1 | 2 | 3 |
| Per-move target $R^*(M)$ | 0.9655 | 0.9074 | 0.8842 | 0.8691 |

</div>
</div>

The [scheduling target](docs.topics.move-recall.move-recall.md.html#33-the-scheduler-targets-a-09-pass-chance) in the record lists every length.

</section>

<section class="card" id="earlier">

## The two earlier arms predicted the whole line, so line length had to sit in the weights

The 2026-11-13 experiment trained two arms, A2 and B2, with multiplicative memory and the earlier grading rule, under which a pass meant a review without any mistake. In both, FSRS recall meant the chance of passing the whole line:

<div class="scroll" role="region" aria-label="Earlier arms A2 and B2; scroll horizontally on narrow screens" tabindex="0" data-reader-horizontal style="overflow-x:auto">
<div style="min-width:560px">

| | A2 | B2 |
|---|---|---|
| Learns from | pass or fail of each review (pass = no mistakes) | the hidden true chance of a clean review, $R^M$ |
| Usable with real players | yes | no: $R^M$ exists only inside the simulator |
| Information per review | one bit | the hidden chance itself |

</div>
</div>

**Why that limits both.** The chance of a clean line, $R^M$, falls faster the longer the line is. FSRS has one forgetting curve for all lines, so one set of weights cannot fit short and long lines at once. The new model puts the line length into $p_\text{pass}(R, M)$ instead of into the weights; the [record's arithmetic](docs.topics.move-recall.move-recall.md.html#32-fsrs-recall-means-one-move) shows the difference.

### The same review gives each arm a different target

Take one review: a 6-move line with one mistake. Under the decided grading rule it is a pass.

<div class="scroll" role="region" aria-label="Training target of one review per arm; scroll horizontally on narrow screens" tabindex="0" data-reader-horizontal style="overflow-x:auto">
<div style="min-width:620px">

| Arm | Target of this review | What it learns |
|---|---|---|
| A2 (earlier) | 0 | failed, although 5 of 6 moves were right |
| B2 (earlier) | the hidden $R^6$, for example 0.531 at $R = 0.9$ | the true clean chance, but only in simulation |
| A1c-pass (new) | 1 | passed, the same label as a review without mistakes |
| A1c-acc (new) | $5/6 = 0.83$ | how much of the line was recalled |

</div>
</div>

**Why accuracy.** Accuracy is the observable counterpart of B2's hidden target. On average it equals the per-move recall $R$, so every review tells how well the line was known, not just whether it passed. It is already exported for bots and real players, and it does not depend on the mistake limits: if they change, only $R^*(M)$ is recomputed. The gain is largest on long lines a player knows well, where almost every review passes and a pass says little; the [training approaches](docs.topics.move-recall.approaches.md.html#3-approach-1-accuracy-target) record quantifies it.

</section>

<section class="card" id="training">

## Both new arms are judged on the pass chance; only what they train on differs

<p class="bs-lead">Both per-move arms schedule and are scored by the pass chance. A1c-acc fits per-move recall to accuracy and never computes the pass chance while it learns; A1c-pass fits the pass chance to pass or fail.</p>

<div class="scroll" role="region" aria-label="Where the pass chance enters each arm; scroll horizontally on narrow screens" tabindex="0" data-reader-horizontal style="overflow-x:auto">
<div style="min-width:640px">

| Stage | A1c-acc (accuracy) | A1c-pass (pass chance) |
|---|---|---|
| Training: what is compared | $R$ with the accuracy | $p_\text{pass}(R, M)$ with pass or fail |
| Scheduling: when the line is due | $p_\text{pass}(R, M)$ falls to 0.9 | the same |
| Evaluation: what is scored | $p_\text{pass}(R, M)$ against real passes and the hidden pass chance | the same |

</div>
</div>

The line-level arms A1 and A1c are scored on the same passes and hidden pass chance with their own line-level recall, so all four arms are compared on one quantity. The experiment therefore asks whether the extra information in accuracy gives better pass-chance predictions than training on pass or fail directly.

### What each target risks

<div class="scroll" role="region" aria-label="Trade-off between the two targets; scroll horizontally on narrow screens" tabindex="0" data-reader-horizontal style="overflow-x:auto">
<div style="min-width:620px">

| | A1c-acc (accuracy) | A1c-pass (pass chance) |
|---|---|---|
| Uses | the number of mistakes | pass or fail only |
| If the mistake limits change | the weights stay valid | refit needed |
| If real mistakes come in clusters | $R$ stays the mean move recall, but the computed pass chance is too high | the pass chance stays calibrated, but $R$ loses its per-move meaning |

</div>
</div>

In the simulator every move is drawn independently, so accuracy is expected to fit at least as well; that is a prediction, not a result. Whether real players' mistakes cluster, for example after forgetting a branch point, only real reviews can show, so both are trained. The [side-by-side comparison](docs.topics.move-recall.approaches.md.html#5-side-by-side) in the record has the full list.

</section>
