+++
toc = []
title = "Session grading"
slug = "session-grading"
description = "Follow the decided rule that turns one finished Repeating review into Again, Hard, Good or Easy, and how it differs from the earlier rule."
brand_sub = "mistake limits · time bands · FSRS grade"
components = ["toc", "nav", "code", "filelinks"]
page_css = ["build-sheet.css"]
math = true
+++

# Session grading

<section class="card" id="rule">

## A review is graded by its mistakes first and its time second

<p class="bs-lead">A finished Repeating review is Again when it has more mistakes than its line length allows; otherwise the mean time of the moves the player knew picks Easy, Good or Hard. The rule was decided on 2026-11-16 and now runs in the app and the simulator; the training data and weights still come from the earlier rule.</p>

<div class="bs-checks">
<div class="bs-check"><span class="bs-badge bs-ok">Decided</span><h3>Rule decided on 2026-11-16</h3><p>Mistake limits by line length, four time bands, Easy only without mistakes.</p></div>
<div class="bs-check"><span class="bs-badge bs-ok">Implemented</span><h3>The app and the simulator use the rule</h3><p>Added in commit <code>52e9535</code>. Synthetic datasets and weights recorded before the move-recall retraining, including the app's weights, were graded with the earlier rule.</p></div>
<div class="bs-check"><span class="bs-badge bs-wait">Not calibrated</span><h3>The time values are starting values</h3><p>Chosen from published orders of magnitude, not from human data. They are checked once the app records browser times.</p></div>
</div>

<figure id="fig-rule">
<div class="bs-flow" role="img" aria-label="A finished review gives the number of player moves, which of them were right on the first attempt, and the browser time of each move. The mistake count is compared with the line's mistake limit: over the limit gives Again, exactly at the limit gives Hard. Below the limit, the time band of the timed moves picks Easy, Good or Hard.">
<div class="bs-node bs-violet"><span class="bs-label">Finished review</span><b>Moves, mistakes, times</b><p>The player plays the whole line; a wrong move is taken back and retried until it is right.</p></div>
<div class="bs-arrow"><span>count</span></div>
<div class="bs-node bs-orange"><span class="bs-label">First: mistakes</span><b>Compare with the limit</b><p>Over the line's limit: Again. Exactly at it: Hard. Below it: time decides.</p></div>
<div class="bs-arrow"><span>then time</span></div>
<div class="bs-node bs-teal"><span class="bs-label">Second: time band</span><b>Easy, Good or Hard</b><p>Fast, Normal, Slow or Very slow, from the mean time of the moves the player knew.</p></div>
</div>
<figcaption><strong>Figure 1.</strong> Order of the two checks in the <a href="docs.topics.session-grading.session-grading.md.html#35-decision-procedure">decision procedure</a>. Arrows show the order of the checks, not code that runs today. Generator: this page's HTML.</figcaption>
</figure>

[Figure 1](#fig-rule) shows the two signals the grade uses: recall, counted as mistakes, and fluency, measured as time. No third signal is added. The rule receives one finished review and returns one grade; it optimizes nothing and has no per-player settings. Four terms carry the rest of this page:

- **$M$**, the number of moves the player plays in the line. Opponent moves do not count.
- **A mistake** is a player move whose first attempt was wrong. Further wrong attempts on the same move add no mistakes. **$k$** is the number of mistakes in the review.
- **The mistake limit $L(M)$** is the most mistakes a review may have without being Again. **The Good limit $G(M) = \max(0,\ L(M) - 1)$** is the most mistakes a review may have and still be Good.
- **$\bar{T}$** is the mean time of the timed moves, explained in [the time chapter](#time).

### What changed from the earlier rule

The simulator and the app ran the earlier rule until commit `52e9535`, and every recorded dataset and trained weight was graded with it. The table compares it with the decided rule, point by point.

<div class="scroll" role="region" aria-label="Earlier and decided grading rule compared; scroll horizontally on narrow screens" tabindex="0" data-reader-horizontal style="overflow-x:auto">
<div style="min-width:760px">

| Question | Earlier rule (replaced) | Decided rule (2026-11-16) |
|---|---|---|
| What does one mistake do? | Again, on every line. | Again only on lines of 3 moves or fewer. Hard on 4–7 moves. On 8 moves or more it can still be Good. |
| How many mistakes give Again? | Any. | More than the line's limit: 0, 1, 2 or 3 by line length. |
| Which time is graded? | All time divided by the moves, minus the player's physical move time (`baseline_ms`). | The mean of the first-try correct moves without the line's first move, each capped at 20000 ms. Nothing is subtracted. |
| Where is time measured? | On the server in the app, where the baseline is zero. | In the browser. |
| Time boundaries | Easy below 500 ms, Good from 500 to 1,800 ms, Hard above 1,800 ms. | Fast below 1500 ms, Normal up to 3500 ms, Slow up to 8000 ms, Very slow above. |
| Can a review without mistakes be Hard? | Yes, above 1,800 ms. | Only when Very slow, above 8000 ms. |
| Can a review with mistakes be Easy? | No. | No. |

</div>
</div>

The [session grading record](docs.topics.session-grading.session-grading.md.html#7-decisions-and-rationale) is the canonical text of the rule. Its decisions section gives each choice with its date and its reason, and names the alternatives that were not taken. The [earlier rule](docs.topics.session-grading.session-grading.md.html#71-earlier-rule-superseded) stays there as the superseded version.

</section>

<section class="card" id="mistake-limits">

## Longer lines may have more mistakes before the review counts as forgotten

<p class="bs-lead">The limit is 0 mistakes on 3-move lines, 1 on 4–7, 2 on 8–12 and 3 on 13 or more; one mistake more than the limit gives Again.</p>

<div class="scroll" role="region" aria-label="Mistake limits by line length; scroll horizontally on narrow screens" tabindex="0" data-reader-horizontal style="overflow-x:auto">
<div style="min-width:620px">

| Line length $M$ | Mistake limit $L(M)$ | Good limit $G(M)$ | Lines in the catalog |
|---|---|---|---|
| 3 or fewer | 0 | 0 | 164 (6.0%) |
| 4–7 | 1 | 0 | 2,000 (73.6%) |
| 8–12 | 2 | 1 | 528 (19.4%) |
| 13 or more | 3 | 2 | 27 (1.0%) |

</div>
</div>

The catalog counts are measured on the 2,719 lines of the app's catalog ([record section 8.1](docs.topics.session-grading.session-grading.md.html#81-catalog-line-lengths-measured)). The largest limit, 3, stays below the 4 wrong attempts at which the app already makes the player relearn the line.

<figure id="fig-again-chance">
<div role="region" aria-label="Again chance by line length for the compared rules; scroll horizontally on narrow screens" tabindex="0" data-reader-horizontal style="overflow-x:auto">
<svg viewBox="0 0 780 420" role="img" aria-labelledby="again-title again-desc" style="display:block;width:100%;min-width:716px;max-width:1100px;height:auto">
<title id="again-title">Again chance by line length at per-move recall 0.9, for the four compared mistake rules</title>
<desc id="again-desc">With any mistake giving Again, the Again chance climbs from 27% on 3-move lines to 77% on 14-move lines. The decided limits keep it between 3% and 15% for lines of 4 to 14 moves: it rises within each length band and drops where the limit rises, from 15% at 7 moves to 4% at 8. 3-move lines stay at 27% under every rule. Design arithmetic assuming independent per-move recall, not a measurement.</desc>
<rect x="82" y="60" width="56" height="300" fill="#18202b"/>
<text x="110" y="80" text-anchor="middle" font-size="13" font-weight="700" fill="#e6edf3">3 moves</text>
<text x="110" y="97" text-anchor="middle" font-size="13" fill="#39d2c0">limit 0</text>
<rect x="138" y="60" width="224" height="300" fill="#131922"/>
<text x="250" y="80" text-anchor="middle" font-size="13" font-weight="700" fill="#e6edf3">4–7 moves</text>
<text x="250" y="97" text-anchor="middle" font-size="13" fill="#39d2c0">limit 1</text>
<rect x="362" y="60" width="280" height="300" fill="#18202b"/>
<text x="502" y="80" text-anchor="middle" font-size="13" font-weight="700" fill="#e6edf3">8–12 moves</text>
<text x="502" y="97" text-anchor="middle" font-size="13" fill="#39d2c0">limit 2</text>
<rect x="642" y="60" width="112" height="300" fill="#131922"/>
<text x="698" y="80" text-anchor="middle" font-size="13" font-weight="700" fill="#e6edf3">13+ moves</text>
<text x="698" y="97" text-anchor="middle" font-size="13" fill="#39d2c0">limit 3</text>
<line x1="82" x2="754" y1="360" y2="360" stroke="#252c36" stroke-width="1"/>
<text x="74" y="364" text-anchor="end" font-size="12" fill="#8b949e">0%</text>
<line x1="82" x2="754" y1="300" y2="300" stroke="#252c36" stroke-width="1"/>
<text x="74" y="304" text-anchor="end" font-size="12" fill="#8b949e">20%</text>
<line x1="82" x2="754" y1="240" y2="240" stroke="#252c36" stroke-width="1"/>
<text x="74" y="244" text-anchor="end" font-size="12" fill="#8b949e">40%</text>
<line x1="82" x2="754" y1="180" y2="180" stroke="#252c36" stroke-width="1"/>
<text x="74" y="184" text-anchor="end" font-size="12" fill="#8b949e">60%</text>
<line x1="82" x2="754" y1="120" y2="120" stroke="#252c36" stroke-width="1"/>
<text x="74" y="124" text-anchor="end" font-size="12" fill="#8b949e">80%</text>
<text x="20" y="240" text-anchor="middle" font-size="12" fill="#8b949e" transform="rotate(-90 20 240)">Again chance</text>
<text x="110" y="380" text-anchor="middle" font-size="12" fill="#c9d1d9">3</text>
<text x="166" y="380" text-anchor="middle" font-size="12" fill="#c9d1d9">4</text>
<text x="222" y="380" text-anchor="middle" font-size="12" fill="#c9d1d9">5</text>
<text x="278" y="380" text-anchor="middle" font-size="12" fill="#c9d1d9">6</text>
<text x="334" y="380" text-anchor="middle" font-size="12" fill="#c9d1d9">7</text>
<text x="390" y="380" text-anchor="middle" font-size="12" fill="#c9d1d9">8</text>
<text x="446" y="380" text-anchor="middle" font-size="12" fill="#c9d1d9">9</text>
<text x="502" y="380" text-anchor="middle" font-size="12" fill="#c9d1d9">10</text>
<text x="558" y="380" text-anchor="middle" font-size="12" fill="#c9d1d9">11</text>
<text x="614" y="380" text-anchor="middle" font-size="12" fill="#c9d1d9">12</text>
<text x="670" y="380" text-anchor="middle" font-size="12" fill="#c9d1d9">13</text>
<text x="726" y="380" text-anchor="middle" font-size="12" fill="#c9d1d9">14</text>
<text x="418" y="406" text-anchor="middle" font-size="12" fill="#8b949e">Player moves in the line (M)</text>
<polyline points="110,279 166,258 222,237 278,219 334,204 390,189 446,177 502,165 558,153 614,144 670,135 726,129" fill="none" stroke="#8b949e" stroke-width="2" stroke-dasharray="6 5" stroke-linejoin="round"/>
<polyline points="110,279 166,345 222,336 278,327 334,315 390,303 446,291 502,339 558,333 614,327 670,321 726,312" fill="none" stroke="#bc8cff" stroke-width="2" stroke-dasharray="2 4" stroke-linejoin="round"/>
<polyline points="110,279 166,345 222,336 278,327 334,351 390,348 446,345 502,357 558,354 614,351 670,351 726,357" fill="none" stroke="#ffa657" stroke-width="2" stroke-dasharray="10 4 2 4" stroke-linejoin="round"/>
<polyline points="110,279 166,345 222,336 278,327 334,315 390,348 446,345 502,339 558,333 614,327 670,351 726,348" fill="none" stroke="#39d2c0" stroke-width="3.5" stroke-linejoin="round"/>
<text x="726" y="119" text-anchor="middle" font-size="12" fill="#8b949e">77%</text>
<circle cx="110" cy="279" r="4" fill="#39d2c0"/>
<text x="110" y="269" text-anchor="middle" font-size="12" font-weight="700" fill="#39d2c0">27%</text>
<circle cx="166" cy="345" r="4" fill="#39d2c0"/>
<text x="166" y="335" text-anchor="middle" font-size="12" font-weight="700" fill="#39d2c0">5%</text>
<circle cx="222" cy="336" r="4" fill="#39d2c0"/>
<text x="222" y="326" text-anchor="middle" font-size="12" font-weight="700" fill="#39d2c0">8%</text>
<circle cx="278" cy="327" r="4" fill="#39d2c0"/>
<text x="278" y="317" text-anchor="middle" font-size="12" font-weight="700" fill="#39d2c0">11%</text>
<circle cx="334" cy="315" r="4" fill="#39d2c0"/>
<text x="334" y="305" text-anchor="middle" font-size="12" font-weight="700" fill="#39d2c0">15%</text>
<circle cx="390" cy="348" r="4" fill="#39d2c0"/>
<text x="390" y="338" text-anchor="middle" font-size="12" font-weight="700" fill="#39d2c0">4%</text>
<circle cx="446" cy="345" r="4" fill="#39d2c0"/>
<text x="446" y="335" text-anchor="middle" font-size="12" font-weight="700" fill="#39d2c0">5%</text>
<circle cx="502" cy="339" r="4" fill="#39d2c0"/>
<text x="502" y="329" text-anchor="middle" font-size="12" font-weight="700" fill="#39d2c0">7%</text>
<circle cx="558" cy="333" r="4" fill="#39d2c0"/>
<text x="558" y="323" text-anchor="middle" font-size="12" font-weight="700" fill="#39d2c0">9%</text>
<circle cx="614" cy="327" r="4" fill="#39d2c0"/>
<text x="614" y="317" text-anchor="middle" font-size="12" font-weight="700" fill="#39d2c0">11%</text>
<circle cx="670" cy="351" r="4" fill="#39d2c0"/>
<text x="670" y="341" text-anchor="middle" font-size="12" font-weight="700" fill="#39d2c0">3%</text>
<circle cx="726" cy="348" r="4" fill="#39d2c0"/>
<text x="726" y="338" text-anchor="middle" font-size="12" font-weight="700" fill="#39d2c0">4%</text>
<line x1="82" x2="110" y1="24" y2="24" stroke="#8b949e" stroke-width="2" stroke-dasharray="6 5"/>
<text x="118" y="28" font-size="13" fill="#c9d1d9">Any mistake</text>
<line x1="232" x2="260" y1="24" y2="24" stroke="#bc8cff" stroke-width="2" stroke-dasharray="2 4"/>
<text x="268" y="28" font-size="13" fill="#c9d1d9">0/1/2 by 3 &#124; 4–9 &#124; 10+</text>
<line x1="447" x2="475" y1="24" y2="24" stroke="#ffa657" stroke-width="2" stroke-dasharray="10 4 2 4"/>
<text x="483" y="28" font-size="13" fill="#c9d1d9">Accuracy below 70%</text>
<line x1="637" x2="665" y1="24" y2="24" stroke="#39d2c0" stroke-width="3.5"/>
<text x="673" y="28" font-size="13" fill="#c9d1d9">Decided 0/1/2/3</text>
</svg>
</div>
<figcaption><strong>Figure 2.</strong> Chance that a review is Again, by line length, when each move is right independently with chance 0.9. Design arithmetic from <a href="docs.topics.session-grading.session-grading.md.html#82-again-chance-by-rule-design-arithmetic">record section 8.2</a>, not a simulation or a measurement. Shaded columns are the decided length bands of <a href="docs.topics.session-grading.session-grading.md.html#32-mistake-limits-by-line-length">section 3.2</a>. Generator: this page's HTML.</figcaption>
</figure>

[Figure 2](#fig-again-chance) compares the four rules that were considered. Three things stand out:

- **Any mistake gives Again** (the earlier rule) punishes length. A player who knows each move 9 times out of 10 fails a 14-move line 77% of the time.
- **The decided limits** keep Again between 3% and 15% on lines of 4 to 14 moves. Over the whole catalog it averages 9.5%, close to the 10% failure rate that a desired retention of 0.9 expects.
- **Accuracy below 70%** gives the fewest Again grades on long lines, because it is lenient there: on 14-move lines it allows 4 mistakes, the point at which the app already forces a relearn. It was rejected.

The decided limits still separate remembering from forgetting. When per-move recall falls, the catalog-average Again chance rises steeply:

<div class="bs-specs">
<div><span class="bs-label">Recall 0.95</span><b>3.0%<small> Again</small></b></div>
<div><span class="bs-label">Recall 0.9</span><b>9.5%<small> Again</small></b></div>
<div><span class="bs-label">Recall 0.8</span><b>29.4%<small> Again</small></b></div>
<div><span class="bs-label">Recall 0.7</span><b>51.4%<small> Again</small></b></div>
</div>

### Why a table of limits instead of an accuracy share

A fixed accuracy share is harsh on short lines: a 3-move line can only reach 100%, 67%, 33% or 0%. On long lines it turns Again into a cliff at the boundary. A fixed mistake count is harsh on long lines instead. For the catalog's lines of 3 to 14 moves, an 80% share already works out as whole-mistake limits, so a table of limits says the same thing and is easier to explain ([record section 7.3](docs.topics.session-grading.session-grading.md.html#73-mistake-limits-by-length-not-one-accuracy-share)).

Any table of whole mistakes has two known weak spots, both visible in [Figure 2](#fig-again-chance). Again drops sharply where the limit rises, from 15% at 7 moves to 4% at 8. And 3-move lines stay strict, at 27%, because they allow no mistake at all. The figures assume that each move is right independently of the others; real mistakes probably cluster after a forgotten branch point.

<!-- fold: dead-end The compared rules in numbers -->

Mistake limits each rule gives, by player moves in the line:

<div class="scroll" role="region" aria-label="Mistake limits of the compared rules; scroll horizontally on narrow screens" tabindex="0" data-reader-horizontal style="overflow-x:auto">
<div style="min-width:760px">

| Rule | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 | 14 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Any mistake | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 0/1/2 (3 \| 4–9 \| 10+) | 0 | 1 | 1 | 1 | 1 | 1 | 1 | 2 | 2 | 2 | 2 | 2 |
| **Decided** 0/1/2/3 (3 \| 4–7 \| 8–12 \| 13+) | 0 | 1 | 1 | 1 | 1 | 2 | 2 | 2 | 2 | 2 | 3 | 3 |
| Accuracy below 70% | 0 | 1 | 1 | 1 | 2 | 2 | 2 | 3 | 3 | 3 | 3 | 4 |

</div>
</div>

Again chance when each move is right with chance 0.8:

<div class="scroll" role="region" aria-label="Again chance of the compared rules at recall 0.8; scroll horizontally on narrow screens" tabindex="0" data-reader-horizontal style="overflow-x:auto">
<div style="min-width:860px">

| Rule | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 | 14 | Catalog average |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Any mistake | 49% | 59% | 67% | 74% | 79% | 83% | 87% | 89% | 91% | 93% | 95% | 96% | 70.9% |
| 0/1/2 | 49% | 18% | 26% | 34% | 42% | 50% | 56% | 32% | 38% | 44% | 50% | 55% | 33.6% |
| **Decided** | 49% | 18% | 26% | 34% | 42% | 20% | 26% | 32% | 38% | 44% | 25% | 30% | 29.4% |
| Accuracy below 70% | 49% | 18% | 26% | 34% | 15% | 20% | 26% | 12% | 16% | 21% | 25% | 13% | 24.6% |

</div>
</div>

At recall 0.9 the catalog averages are 45.4% for any mistake, 11.8% for 0/1/2, 9.5% for the decided limits and 7.6% for accuracy below 70%. The catalog average weights each length by its number of lines; it covers 2,718 of the 2,719 lines, all but the single 18-move line. Exact values per length are in [record section 8.2](docs.topics.session-grading.session-grading.md.html#82-again-chance-by-rule-design-arithmetic).

<!-- /fold -->

</section>

<section class="card" id="time">

## Time counts only the moves the player knew, and sorts the review into four bands

<p class="bs-lead">The browser times each move; the mean of the first-try correct moves after the first, each capped at 20000 ms, puts the review in the Fast, Normal, Slow or Very slow band.</p>

<figure id="fig-timing">
<div class="bs-flow" role="img" aria-label="The browser starts a move's timer when the position with the player to move is shown and stops it when the player makes the move. Moves with a mistake and the line's first player move are dropped. Each remaining time is capped at 20000 ms and the mean of the capped times gives the band.">
<div class="bs-node bs-violet"><span class="bs-label">Measure</span><b>Browser timer per move</b><p>Starts when the position is shown with the player to move, after the opponent's reply is drawn. Stops when the player drops the piece or makes the second click.</p></div>
<div class="bs-arrow"><span>keep</span></div>
<div class="bs-node bs-orange"><span class="bs-label">Timed moves</span><b>Known moves only</b><p>Drop every move with a mistake. Drop the line's first player move.</p></div>
<div class="bs-arrow"><span>cap, average</span></div>
<div class="bs-node bs-teal"><span class="bs-label">Mean time</span><b>One band</b><p>Each time counts at most 20000 ms. The mean of the capped times picks the band. No timed moves: Normal.</p></div>
</div>
<figcaption><strong>Figure 3.</strong> How the graded time is measured, from <a href="docs.topics.session-grading.session-grading.md.html#33-measuring-the-time">record section 3.3</a>. The app does not measure time this way yet; it measures on the server. Generator: this page's HTML.</figcaption>
</figure>

[Figure 3](#fig-timing) ends in one number. With $n$ timed moves of times $t_1, \dots, t_n$ in milliseconds,

$$\bar{T} = \frac{1}{n}\sum_{i=1}^{n} \min(t_i,\ 20000)$$

Retries and the time spent copying the hint never enter $\bar{T}$; mistakes are counted once, in $k$. Nothing is subtracted from any time.

<figure id="fig-bands">
<div role="region" aria-label="Time bands on a logarithmic axis; scroll horizontally on narrow screens" tabindex="0" data-reader-horizontal style="overflow-x:auto">
<svg viewBox="0 0 780 250" role="img" aria-labelledby="bands-title bands-desc" style="display:block;width:100%;min-width:716px;max-width:1100px;height:auto">
<title id="bands-title">The four time bands on a logarithmic time axis</title>
<desc id="bands-desc">Mean move time on a logarithmic axis. Fast is below 1500 ms, Normal from 1500 to 3500 ms, Slow above 3500 up to 8000 ms and Very slow above 8000 ms. Each move time is capped at 20000 ms. Below 1500 ms the line was played from recognition; above 3500 ms the player had to think; above 8000 ms the player worked the line out; the cap stops one interruption from deciding the band. On this axis the boundaries are about evenly spaced.</desc>
<rect x="30.0" y="62" width="191.8" height="58" fill="#57ab5a" fill-opacity="0.18" stroke="#57ab5a" stroke-width="1.5"/>
<text x="125.9" y="88" text-anchor="middle" font-size="16" font-weight="700" fill="#e6edf3">Fast</text>
<text x="125.9" y="108" text-anchor="middle" font-size="12" fill="#c9d1d9">below 1500 ms</text>
<rect x="221.8" y="62" width="165.6" height="58" fill="#39d2c0" fill-opacity="0.18" stroke="#39d2c0" stroke-width="1.5"/>
<text x="304.6" y="88" text-anchor="middle" font-size="16" font-weight="700" fill="#e6edf3">Normal</text>
<text x="304.6" y="108" text-anchor="middle" font-size="12" fill="#c9d1d9">1500–3500 ms</text>
<rect x="387.4" y="62" width="161.5" height="58" fill="#ffa657" fill-opacity="0.18" stroke="#ffa657" stroke-width="1.5"/>
<text x="468.2" y="88" text-anchor="middle" font-size="16" font-weight="700" fill="#e6edf3">Slow</text>
<text x="468.2" y="108" text-anchor="middle" font-size="12" fill="#c9d1d9">3500–8000 ms</text>
<rect x="548.9" y="62" width="179.0" height="58" fill="#f47067" fill-opacity="0.18" stroke="#f47067" stroke-width="1.5"/>
<text x="638.4" y="88" text-anchor="middle" font-size="16" font-weight="700" fill="#e6edf3">Very slow</text>
<text x="638.4" y="108" text-anchor="middle" font-size="12" fill="#c9d1d9">above 8000 ms</text>
<rect x="728.0" y="62" width="22.0" height="58" fill="none" stroke="#8b949e" stroke-dasharray="3 3"/>
<line x1="221.8" x2="221.8" y1="46" y2="138" stroke="#e6edf3" stroke-width="1.5"/>
<text x="221.8" y="38" text-anchor="middle" font-size="13" font-weight="700" fill="#e6edf3">1500 ms</text>
<text x="221.8" y="158" text-anchor="middle" font-size="12" fill="#c9d1d9">below: played</text>
<text x="221.8" y="174" text-anchor="middle" font-size="12" fill="#c9d1d9">from recognition</text>
<line x1="387.4" x2="387.4" y1="46" y2="138" stroke="#e6edf3" stroke-width="1.5"/>
<text x="387.4" y="38" text-anchor="middle" font-size="13" font-weight="700" fill="#e6edf3">3500 ms</text>
<text x="387.4" y="158" text-anchor="middle" font-size="12" fill="#c9d1d9">above: the player</text>
<text x="387.4" y="174" text-anchor="middle" font-size="12" fill="#c9d1d9">had to think</text>
<line x1="548.9" x2="548.9" y1="46" y2="138" stroke="#e6edf3" stroke-width="1.5"/>
<text x="548.9" y="38" text-anchor="middle" font-size="13" font-weight="700" fill="#e6edf3">8000 ms</text>
<text x="548.9" y="158" text-anchor="middle" font-size="12" fill="#c9d1d9">above: worked the</text>
<text x="548.9" y="174" text-anchor="middle" font-size="12" fill="#c9d1d9">line out</text>
<line x1="728.0" x2="728.0" y1="46" y2="138" stroke="#e6edf3" stroke-width="1.5"/>
<text x="750.0" y="38" text-anchor="end" font-size="13" font-weight="700" fill="#e6edf3">20000 ms cap</text>
<text x="750.0" y="158" text-anchor="end" font-size="12" fill="#c9d1d9">one interruption</text>
<text x="750.0" y="174" text-anchor="end" font-size="12" fill="#c9d1d9">cannot decide</text>
<line x1="30" x2="750" y1="204" y2="204" stroke="#8b949e" stroke-width="1"/>
<path d="M750 204 l-8 -4 v8z" fill="#8b949e"/>
<text x="30" y="228" font-size="12" fill="#8b949e">Mean time of the timed moves, logarithmic axis</text>
<text x="750" y="228" text-anchor="end" font-size="12" fill="#8b949e">slower →</text>
</svg>
</div>
<figcaption><strong>Figure 4.</strong> The four time bands and what each boundary means, from <a href="docs.topics.session-grading.session-grading.md.html#34-time-bands">record section 3.4</a>. The axis is logarithmic: each boundary is about 2.3–2.5 times the one before. Generator: this page's HTML.</figcaption>
</figure>

[Figure 4](#fig-bands) shows the bands on a logarithmic axis, where they come out about evenly spaced. That matches how response times spread: by factors, not by fixed amounts. The bands are exact at their edges:

<div class="scroll" role="region" aria-label="Time constants, band conditions and published support; scroll horizontally on narrow screens" tabindex="0" data-reader-horizontal style="overflow-x:auto">
<div style="min-width:980px">

| Constant | Value | Band condition | What the boundary means | Published support |
|---|---|---|---|---|
| <code style="white-space:nowrap">T_EASY_MS</code> | <span style="white-space:nowrap">1500 ms</span> | Fast: $\bar{T} < 1500$ | Below it the line was played from recognition; the time is mostly the physical move. | Strong players take in chess relations automatically ([Reingold et al. 2001](https://link.springer.com/article/10.3758/BF03196185)); online players think little in the opening ([Russek et al. 2025](https://cocosci.princeton.edu/papers/RussekThinking2025.pdf)). Pointing takes roughly 0.4–1.3 s per movement, dragging is slower, mouse and touch differ ([MacKenzie et al. 2009](https://yorku.ca/mack/hfes2009.html)), so the value leaves room for the physical move. |
| <code style="white-space:nowrap">T_SLOW_MS</code> | <span style="white-space:nowrap">3500 ms</span> | Normal: $1500 \le \bar{T} \le 3500$ | Above it the player had to think. It lowers only reviews **with** mistakes below the limit, from Good to Hard. | In 3-minute blitz, about 5 s, the slowest quarter of moves, marks real thinking ([Lichess blog](https://lichess.org/ublog/Kwxe88CS/redirect)). The value is below 5 s because $\bar{T}$ is a mean over known moves. |
| <code style="white-space:nowrap">T_VERY_SLOW_MS</code> | <span style="white-space:nowrap">8000 ms</span> | Slow: $3500 < \bar{T} \le 8000$; Very slow: $\bar{T} > 8000$ | Above it the player worked the line out rather than remembered it. It is the only time that lowers a review **without** mistakes, from Good to Hard. | One ARTS mastery criterion was 4 correct answers in a row, each under 7 s ([Mettler, Massey & Kellman 2011](https://kellmanlab.psych.ucla.edu/files/mettler_massey_kellman_2011.pdf)). |
| <code style="white-space:nowrap">CAP_MS</code> | <span style="white-space:nowrap">20000 ms</span> | Applied to each move time | Stops one interruption from deciding the band. | SlimStampen caps observed times because interruptions inflate them ([Sense et al. 2016](https://pubmed.ncbi.nlm.nih.gov/26748838/)). |

</div>
</div>

No published source gives cut-offs for this task. The sources support what each boundary means and its order of magnitude, not its exact value. FSRS itself uses no response time; an Anki add-on with a similar shape, Easy under 1 s and Hard from 7 s, gives no justification for its values ([record section 8.4](docs.topics.session-grading.session-grading.md.html#84-published-research-behind-the-time-constants)).

### Why the time is measured this way

<div class="bs-grid g3">
<div class="bs-part bs-violet"><span class="bs-label">Only first-try correct moves</span><p>Keeps time and mistakes independent. Timing retries or the copied hint would count a mistake twice.</p></div>
<div class="bs-part bs-violet"><span class="bs-label">First move left out</span><p>Its time includes taking in the board.</p></div>
<div class="bs-part bs-violet"><span class="bs-label">Browser, not server</span><p>Server intervals add network round trips and rendering to every move, an offset that depends on the device and the connection.</p></div>
<div class="bs-part bs-orange"><span class="bs-label">Each move capped</span><p>A notification or a tab switch must not decide the grade. Capping observed times is standard in learning systems that use response times.</p></div>
<div class="bs-part bs-orange"><span class="bs-label">Same values for every player</span><p>A known opening move should be playable within these times on any device. No baseline is subtracted, because the app cannot know a player's baseline. Not taken: comparing with each player's own pace, as SlimStampen does. Accepted cost: slower hands or devices reach Easy less often.</p></div>
<div class="bs-part bs-orange"><span class="bs-label">Slow without mistakes stays Good</span><p>Correct recall is not graded as a struggle because of a slow device or slow hands. The generous Very slow boundary is the safety net for clear struggle. Not taken: one shared slow boundary for both cases.</p></div>
</div>

These reasons are decisions 7.6 to 7.8 of the [record](docs.topics.session-grading.session-grading.md.html#77-time-only-first-try-correct-moves-capped-browser-measured-first-move-excluded). The time values are starting values, not calibrated against human data; [the last chapter](#next) shows how they will be checked.

</section>

<section class="card" id="grades">

## Only a clean, fast review is Easy; at the limit a review is Hard, over it Again

<p class="bs-lead">Mistakes decide first: a review over its limit is Again and one at the limit is Hard whatever the time; below the limit the time band picks the grade, and Easy needs no mistakes at all.</p>

<figure id="fig-grade-matrix">
<div role="region" aria-label="Grade by mistakes and time band; scroll horizontally on narrow screens" tabindex="0" data-reader-horizontal style="overflow-x:auto">
<svg viewBox="0 0 780 300" role="img" aria-labelledby="grade-title grade-desc" style="display:block;width:100%;min-width:716px;max-width:1100px;height:auto">
<title id="grade-title">Grade by mistakes against the line's limits and by time band</title>
<desc id="grade-desc">Rows compare the mistake count with the line's limits; columns are the time bands Fast, Normal, Slow and Very slow. No mistakes: Easy, Good, Good, Hard. Mistakes below the limit, possible only on lines of 8 or more moves: Good, Good, Hard, Hard. At the limit: Hard in every band. Over the limit: Again in every band.</desc>
<text x="333" y="24" text-anchor="middle" font-size="15" font-weight="700" fill="#e6edf3">Fast</text>
<text x="333" y="44" text-anchor="middle" font-size="12" fill="#8b949e">below 1500 ms</text>
<text x="459" y="24" text-anchor="middle" font-size="15" font-weight="700" fill="#e6edf3">Normal</text>
<text x="459" y="44" text-anchor="middle" font-size="12" fill="#8b949e">1500–3500 ms</text>
<text x="585" y="24" text-anchor="middle" font-size="15" font-weight="700" fill="#e6edf3">Slow</text>
<text x="585" y="44" text-anchor="middle" font-size="12" fill="#8b949e">3500–8000 ms</text>
<text x="711" y="24" text-anchor="middle" font-size="15" font-weight="700" fill="#e6edf3">Very slow</text>
<text x="711" y="44" text-anchor="middle" font-size="12" fill="#8b949e">above 8000 ms</text>
<text x="4" y="85" font-size="15" font-weight="700" fill="#e6edf3">No mistakes</text>
<text x="4" y="104" font-size="12" fill="#8b949e">k = 0</text>
<rect x="273" y="62" width="120" height="52" rx="6" fill="#57ab5a" fill-opacity="0.16" stroke="#57ab5a" stroke-width="1.5"/>
<text x="333" y="94" text-anchor="middle" font-size="16" font-weight="700" fill="#e6edf3">4 Easy</text>
<rect x="399" y="62" width="120" height="52" rx="6" fill="#39d2c0" fill-opacity="0.16" stroke="#39d2c0" stroke-width="1.5"/>
<text x="459" y="94" text-anchor="middle" font-size="16" font-weight="700" fill="#e6edf3">3 Good</text>
<rect x="525" y="62" width="120" height="52" rx="6" fill="#39d2c0" fill-opacity="0.16" stroke="#39d2c0" stroke-width="1.5"/>
<text x="585" y="94" text-anchor="middle" font-size="16" font-weight="700" fill="#e6edf3">3 Good</text>
<rect x="651" y="62" width="120" height="52" rx="6" fill="#ffa657" fill-opacity="0.16" stroke="#ffa657" stroke-width="1.5"/>
<text x="711" y="94" text-anchor="middle" font-size="16" font-weight="700" fill="#e6edf3">2 Hard</text>
<text x="4" y="143" font-size="15" font-weight="700" fill="#e6edf3">Mistakes below the limit</text>
<text x="4" y="162" font-size="12" fill="#8b949e">0 &lt; k ≤ G(M); lines of 8+ moves</text>
<rect x="273" y="120" width="120" height="52" rx="6" fill="#39d2c0" fill-opacity="0.16" stroke="#39d2c0" stroke-width="1.5"/>
<text x="333" y="152" text-anchor="middle" font-size="16" font-weight="700" fill="#e6edf3">3 Good</text>
<rect x="399" y="120" width="120" height="52" rx="6" fill="#39d2c0" fill-opacity="0.16" stroke="#39d2c0" stroke-width="1.5"/>
<text x="459" y="152" text-anchor="middle" font-size="16" font-weight="700" fill="#e6edf3">3 Good</text>
<rect x="525" y="120" width="120" height="52" rx="6" fill="#ffa657" fill-opacity="0.16" stroke="#ffa657" stroke-width="1.5"/>
<text x="585" y="152" text-anchor="middle" font-size="16" font-weight="700" fill="#e6edf3">2 Hard</text>
<rect x="651" y="120" width="120" height="52" rx="6" fill="#ffa657" fill-opacity="0.16" stroke="#ffa657" stroke-width="1.5"/>
<text x="711" y="152" text-anchor="middle" font-size="16" font-weight="700" fill="#e6edf3">2 Hard</text>
<text x="4" y="201" font-size="15" font-weight="700" fill="#e6edf3">At the limit</text>
<text x="4" y="220" font-size="12" fill="#8b949e">k = L(M), k &gt; 0</text>
<rect x="273" y="178" width="120" height="52" rx="6" fill="#ffa657" fill-opacity="0.16" stroke="#ffa657" stroke-width="1.5"/>
<text x="333" y="210" text-anchor="middle" font-size="16" font-weight="700" fill="#e6edf3">2 Hard</text>
<rect x="399" y="178" width="120" height="52" rx="6" fill="#ffa657" fill-opacity="0.16" stroke="#ffa657" stroke-width="1.5"/>
<text x="459" y="210" text-anchor="middle" font-size="16" font-weight="700" fill="#e6edf3">2 Hard</text>
<rect x="525" y="178" width="120" height="52" rx="6" fill="#ffa657" fill-opacity="0.16" stroke="#ffa657" stroke-width="1.5"/>
<text x="585" y="210" text-anchor="middle" font-size="16" font-weight="700" fill="#e6edf3">2 Hard</text>
<rect x="651" y="178" width="120" height="52" rx="6" fill="#ffa657" fill-opacity="0.16" stroke="#ffa657" stroke-width="1.5"/>
<text x="711" y="210" text-anchor="middle" font-size="16" font-weight="700" fill="#e6edf3">2 Hard</text>
<text x="4" y="259" font-size="15" font-weight="700" fill="#e6edf3">Over the limit</text>
<text x="4" y="278" font-size="12" fill="#8b949e">k &gt; L(M)</text>
<rect x="273" y="236" width="120" height="52" rx="6" fill="#f47067" fill-opacity="0.16" stroke="#f47067" stroke-width="1.5"/>
<text x="333" y="268" text-anchor="middle" font-size="16" font-weight="700" fill="#e6edf3">1 Again</text>
<rect x="399" y="236" width="120" height="52" rx="6" fill="#f47067" fill-opacity="0.16" stroke="#f47067" stroke-width="1.5"/>
<text x="459" y="268" text-anchor="middle" font-size="16" font-weight="700" fill="#e6edf3">1 Again</text>
<rect x="525" y="236" width="120" height="52" rx="6" fill="#f47067" fill-opacity="0.16" stroke="#f47067" stroke-width="1.5"/>
<text x="585" y="268" text-anchor="middle" font-size="16" font-weight="700" fill="#e6edf3">1 Again</text>
<rect x="651" y="236" width="120" height="52" rx="6" fill="#f47067" fill-opacity="0.16" stroke="#f47067" stroke-width="1.5"/>
<text x="711" y="268" text-anchor="middle" font-size="16" font-weight="700" fill="#e6edf3">1 Again</text>
</svg>
</div>
<figcaption><strong>Figure 5.</strong> Grade for each combination of mistakes and time band, from the <a href="docs.topics.session-grading.session-grading.md.html#35-decision-procedure">decision procedure</a>. The number before each grade is its FSRS value. Generator: this page's HTML.</figcaption>
</figure>

Read [Figure 5](#fig-grade-matrix) row by row:

- **No mistakes.** Fast is Easy. Normal and Slow are Good. Only Very slow lowers the review to Hard.
- **Mistakes below the limit.** Never Easy: Easy requires no mistakes, a choice made directly. Fast and Normal are Good; Slow already lowers the review to Hard. This row exists only on lines of 8 or more moves, because below 8 the Good limit is 0.
- **At the limit.** Hard in every band, so a fast review does not hide the mistakes.
- **Over the limit.** Again in every band.

<!-- fold: code The decision procedure -->

The record states the rule as this procedure ([section 3.5](docs.topics.session-grading.session-grading.md.html#35-decision-procedure)):

```text
L = mistake_limit(M)            # section 3.2
G = max(0, L - 1)
band = time_band(T̄)             # sections 3.3 and 3.4

if k > L:                        return AGAIN
if k == L and k > 0:             return HARD
if k == 0:
    if band == FAST:             return EASY
    if band in (NORMAL, SLOW):   return GOOD
    return HARD                  # VERY_SLOW
# here 0 < k <= G
if band in (FAST, NORMAL):       return GOOD
return HARD                      # SLOW or VERY_SLOW
```

<!-- /fold -->

### Every grade by line length

The full table spells out [Figure 5](#fig-grade-matrix) for each length band. The accuracy column only helps reading: it is the range over the catalog's line lengths in each band, and the rule does not use it.

<div class="scroll" role="region" aria-label="Full grade table by line length; scroll horizontally on narrow screens" tabindex="0" data-reader-horizontal style="overflow-x:auto">
<div style="min-width:760px">

| Line length | Mistakes $k$ | Accuracy | Fast | Normal | Slow | Very slow |
|---|---|---|---|---|---|---|
| 3 or fewer | 0 | 100% | Easy | Good | Good | Hard |
| | 1 or more | ≤ 67% | Again | Again | Again | Again |
| 4–7 | 0 | 100% | Easy | Good | Good | Hard |
| | 1 | 75–86% | Hard | Hard | Hard | Hard |
| | 2 or more | ≤ 71% | Again | Again | Again | Again |
| 8–12 | 0 | 100% | Easy | Good | Good | Hard |
| | 1 | 88–92% | Good | Good | Hard | Hard |
| | 2 | 75–83% | Hard | Hard | Hard | Hard |
| | 3 or more | ≤ 75% | Again | Again | Again | Again |
| 13 or more | 0 | 100% | Easy | Good | Good | Hard |
| | 1–2 | 85–93% | Good | Good | Hard | Hard |
| | 3 | 77–79% | Hard | Hard | Hard | Hard |
| | 4 or more | ≤ 71% | Again | Again | Again | Again |

</div>
</div>

### Worked examples

These reviews come from the record's [test vectors](docs.topics.session-grading.session-grading.md.html#37-test-vectors), which the backend and simulator tests check. Move times are listed per player move in order; `x` marks a move with a mistake, whose time is ignored, and `1000 ×8` means eight moves of 1000 ms. The first move is never timed.

<div class="scroll" role="region" aria-label="Worked grading examples; scroll horizontally on narrow screens" tabindex="0" data-reader-horizontal style="overflow-x:auto">
<div style="min-width:900px">

| Vector | $M$ | Move times (ms) | $k$ | $\bar{T}$ (ms) | Band | Grade | What it shows |
|---|---|---|---|---|---|---|---|
| 1 | 3 | 5000, 900, 1100 | 0 | 1000 | Fast | **Easy** | The slow first move does not count. |
| 3 | 3 | 900, 20000, 1000 | 0 | 10500 | Very slow | **Hard** | On a 3-move line one long pause makes the review Very slow. |
| 4 | 4 | 900, 20000, 1000, 1000 | 0 | 7333 | Slow | **Good** | From 4 moves up the same pause cannot. |
| 6 | 6 | 900, 1000, x, 1200, 1100, 1300 | 1 | 1150 | Fast | **Hard** | One mistake on a 4–7 move line is at the limit; speed does not help. |
| 7 | 6 | 900, x, x, 1000, 1000, 1000 | 2 | 1000 | Fast | **Again** | Two mistakes on a 4–7 move line are over the limit. |
| 8 | 10 | 900, x, 1000 ×8 | 1 | 1000 | Fast | **Good** | One mistake on a 10-move line is below the limit. |
| 9 | 10 | 900, x, 4000 ×8 | 1 | 4000 | Slow | **Hard** | The same review, slow: with a mistake, Slow lowers it. |
| 13 | 8 | 900, 9000 ×7 | 0 | 9000 | Very slow | **Hard** | No mistakes but Very slow. |
| 14 | 8 | 900, 30000, 1000 ×6 | 0 | 3714 | Slow | **Good** | The cap: 30000 counts as 20000, so $(20000 + 6 \times 1000) / 7 \approx 3714$. |

</div>
</div>

Vectors 3 and 4 show a trade-off that was accepted on 2026-11-16. A 3-move line has only two timed moves, so one capped pause and one quick move give a mean of 10500 ms. That was judged real struggle on a short line. Lowering the cap to 15000 ms would remove the case, at the cost of a weaker time signal on every line ([record section 6.4](docs.topics.session-grading.session-grading.md.html#64-one-pause-on-3-move-lines)).

</section>

<section class="card" id="good-with-mistakes">

## Good allows mistakes below the limit, so long lines do not collect Hard grades by chance

<p class="bs-lead">If any mistake capped a review at Hard, a player who knows a long line well would still get Hard most of the time from chance slips; letting Good go up to one mistake below the limit avoids that.</p>

<figure id="fig-hard-share">
<div role="region" aria-label="Share of Hard grades caused by mistakes under two Good rules; scroll horizontally on narrow screens" tabindex="0" data-reader-horizontal style="overflow-x:auto">
<svg viewBox="0 0 780 340" role="img" aria-labelledby="hard-title hard-desc" style="display:block;width:100%;min-width:716px;max-width:1100px;height:auto">
<title id="hard-title">Share of reviews that are Hard because of mistakes, by line length, under two Good rules</title>
<desc id="hard-desc">Two panels, per-move recall 0.95 and 0.9. On 4- and 7-move lines both rules give the same Hard share: 17% and 26% at 0.95, 29% and 37% at 0.9. From 8 moves up, if any mistake capped the grade at Hard, the Hard share keeps rising, to 51% at 0.95 and 73% at 0.9 on 14-move lines; with Good allowed below the limit it stays between 3% and 23%. Design arithmetic, not a measurement.</desc>
<text x="70" y="66" font-size="14" font-weight="700" fill="#e6edf3">Per-move recall r = 0.95</text>
<line x1="70" x2="370" y1="280" y2="280" stroke="#252c36"/>
<text x="62" y="284" text-anchor="end" font-size="12" fill="#8b949e">0%</text>
<line x1="70" x2="370" y1="228" y2="228" stroke="#252c36"/>
<text x="62" y="232" text-anchor="end" font-size="12" fill="#8b949e">20%</text>
<line x1="70" x2="370" y1="176" y2="176" stroke="#252c36"/>
<text x="62" y="180" text-anchor="end" font-size="12" fill="#8b949e">40%</text>
<line x1="70" x2="370" y1="124" y2="124" stroke="#252c36"/>
<text x="62" y="128" text-anchor="end" font-size="12" fill="#8b949e">60%</text>
<line x1="70" x2="370" y1="72" y2="72" stroke="#252c36"/>
<text x="62" y="76" text-anchor="end" font-size="12" fill="#8b949e">80%</text>
<rect x="74.0" y="235.8" width="20" height="44.2" fill="#8b949e" fill-opacity="0.55"/>
<text x="84.0" y="230.8" text-anchor="middle" font-size="12" fill="#c9d1d9">17</text>
<rect x="96.0" y="235.8" width="20" height="44.2" fill="#39d2c0" fill-opacity="0.9"/>
<text x="106.0" y="230.8" text-anchor="middle" font-size="12" fill="#39d2c0">17</text>
<text x="95.0" y="298" text-anchor="middle" font-size="12" fill="#c9d1d9">4</text>
<rect x="124.0" y="212.4" width="20" height="67.6" fill="#8b949e" fill-opacity="0.55"/>
<text x="134.0" y="207.4" text-anchor="middle" font-size="12" fill="#c9d1d9">26</text>
<rect x="146.0" y="212.4" width="20" height="67.6" fill="#39d2c0" fill-opacity="0.9"/>
<text x="156.0" y="207.4" text-anchor="middle" font-size="12" fill="#39d2c0">26</text>
<text x="145.0" y="298" text-anchor="middle" font-size="12" fill="#c9d1d9">7</text>
<rect x="174.0" y="194.2" width="20" height="85.8" fill="#8b949e" fill-opacity="0.55"/>
<text x="184.0" y="189.2" text-anchor="middle" font-size="12" fill="#c9d1d9">33</text>
<rect x="196.0" y="267.0" width="20" height="13.0" fill="#39d2c0" fill-opacity="0.9"/>
<text x="206.0" y="262.0" text-anchor="middle" font-size="12" fill="#39d2c0">5</text>
<text x="195.0" y="298" text-anchor="middle" font-size="12" fill="#c9d1d9">8</text>
<rect x="224.0" y="178.6" width="20" height="101.4" fill="#8b949e" fill-opacity="0.55"/>
<text x="234.0" y="173.6" text-anchor="middle" font-size="12" fill="#c9d1d9">39</text>
<rect x="246.0" y="261.8" width="20" height="18.2" fill="#39d2c0" fill-opacity="0.9"/>
<text x="256.0" y="256.8" text-anchor="middle" font-size="12" fill="#39d2c0">7</text>
<text x="245.0" y="298" text-anchor="middle" font-size="12" fill="#c9d1d9">10</text>
<rect x="274.0" y="165.6" width="20" height="114.4" fill="#8b949e" fill-opacity="0.55"/>
<text x="284.0" y="160.6" text-anchor="middle" font-size="12" fill="#c9d1d9">44</text>
<rect x="296.0" y="254.0" width="20" height="26.0" fill="#39d2c0" fill-opacity="0.9"/>
<text x="306.0" y="249.0" text-anchor="middle" font-size="12" fill="#39d2c0">10</text>
<text x="295.0" y="298" text-anchor="middle" font-size="12" fill="#c9d1d9">12</text>
<rect x="324.0" y="147.4" width="20" height="132.6" fill="#8b949e" fill-opacity="0.55"/>
<text x="334.0" y="142.4" text-anchor="middle" font-size="12" fill="#c9d1d9">51</text>
<rect x="346.0" y="272.2" width="20" height="7.8" fill="#39d2c0" fill-opacity="0.9"/>
<text x="356.0" y="267.2" text-anchor="middle" font-size="12" fill="#39d2c0">3</text>
<text x="345.0" y="298" text-anchor="middle" font-size="12" fill="#c9d1d9">14</text>
<text x="220" y="322" text-anchor="middle" font-size="12" fill="#8b949e">Player moves in the line</text>
<text x="450" y="66" font-size="14" font-weight="700" fill="#e6edf3">Per-move recall r = 0.9</text>
<line x1="450" x2="750" y1="280" y2="280" stroke="#252c36"/>
<text x="442" y="284" text-anchor="end" font-size="12" fill="#8b949e">0%</text>
<line x1="450" x2="750" y1="228" y2="228" stroke="#252c36"/>
<text x="442" y="232" text-anchor="end" font-size="12" fill="#8b949e">20%</text>
<line x1="450" x2="750" y1="176" y2="176" stroke="#252c36"/>
<text x="442" y="180" text-anchor="end" font-size="12" fill="#8b949e">40%</text>
<line x1="450" x2="750" y1="124" y2="124" stroke="#252c36"/>
<text x="442" y="128" text-anchor="end" font-size="12" fill="#8b949e">60%</text>
<line x1="450" x2="750" y1="72" y2="72" stroke="#252c36"/>
<text x="442" y="76" text-anchor="end" font-size="12" fill="#8b949e">80%</text>
<rect x="454.0" y="204.6" width="20" height="75.4" fill="#8b949e" fill-opacity="0.55"/>
<text x="464.0" y="199.6" text-anchor="middle" font-size="12" fill="#c9d1d9">29</text>
<rect x="476.0" y="204.6" width="20" height="75.4" fill="#39d2c0" fill-opacity="0.9"/>
<text x="486.0" y="199.6" text-anchor="middle" font-size="12" fill="#39d2c0">29</text>
<text x="475.0" y="298" text-anchor="middle" font-size="12" fill="#c9d1d9">4</text>
<rect x="504.0" y="183.8" width="20" height="96.2" fill="#8b949e" fill-opacity="0.55"/>
<text x="514.0" y="178.8" text-anchor="middle" font-size="12" fill="#c9d1d9">37</text>
<rect x="526.0" y="183.8" width="20" height="96.2" fill="#39d2c0" fill-opacity="0.9"/>
<text x="536.0" y="178.8" text-anchor="middle" font-size="12" fill="#39d2c0">37</text>
<text x="525.0" y="298" text-anchor="middle" font-size="12" fill="#c9d1d9">7</text>
<rect x="554.0" y="142.2" width="20" height="137.8" fill="#8b949e" fill-opacity="0.55"/>
<text x="564.0" y="137.2" text-anchor="middle" font-size="12" fill="#c9d1d9">53</text>
<rect x="576.0" y="241.0" width="20" height="39.0" fill="#39d2c0" fill-opacity="0.9"/>
<text x="586.0" y="236.0" text-anchor="middle" font-size="12" fill="#39d2c0">15</text>
<text x="575.0" y="298" text-anchor="middle" font-size="12" fill="#c9d1d9">8</text>
<rect x="604.0" y="129.2" width="20" height="150.8" fill="#8b949e" fill-opacity="0.55"/>
<text x="614.0" y="124.2" text-anchor="middle" font-size="12" fill="#c9d1d9">58</text>
<rect x="626.0" y="230.6" width="20" height="49.4" fill="#39d2c0" fill-opacity="0.9"/>
<text x="636.0" y="225.6" text-anchor="middle" font-size="12" fill="#39d2c0">19</text>
<text x="625.0" y="298" text-anchor="middle" font-size="12" fill="#c9d1d9">10</text>
<rect x="654.0" y="121.4" width="20" height="158.6" fill="#8b949e" fill-opacity="0.55"/>
<text x="664.0" y="116.4" text-anchor="middle" font-size="12" fill="#c9d1d9">61</text>
<rect x="676.0" y="220.2" width="20" height="59.8" fill="#39d2c0" fill-opacity="0.9"/>
<text x="686.0" y="215.2" text-anchor="middle" font-size="12" fill="#39d2c0">23</text>
<text x="675.0" y="298" text-anchor="middle" font-size="12" fill="#c9d1d9">12</text>
<rect x="704.0" y="90.2" width="20" height="189.8" fill="#8b949e" fill-opacity="0.55"/>
<text x="714.0" y="85.2" text-anchor="middle" font-size="12" fill="#c9d1d9">73</text>
<rect x="726.0" y="251.4" width="20" height="28.6" fill="#39d2c0" fill-opacity="0.9"/>
<text x="736.0" y="246.4" text-anchor="middle" font-size="12" fill="#39d2c0">11</text>
<text x="725.0" y="298" text-anchor="middle" font-size="12" fill="#c9d1d9">14</text>
<text x="600" y="322" text-anchor="middle" font-size="12" fill="#8b949e">Player moves in the line</text>
<rect x="70" y="14" width="16" height="12" fill="#8b949e" fill-opacity="0.55"/>
<text x="94" y="25" font-size="13" fill="#c9d1d9">Any mistake gives at most Hard (%)</text>
<rect x="420" y="14" width="16" height="12" fill="#39d2c0" fill-opacity="0.9"/>
<text x="444" y="25" font-size="13" fill="#c9d1d9">Decided: Good up to L(M) − 1 (%)</text>
</svg>
</div>
<figcaption><strong>Figure 6.</strong> Share of reviews that are Hard because of mistakes, under the decided mistake limits, for two ways of setting the Good limit. Design arithmetic from <a href="docs.topics.session-grading.session-grading.md.html#83-hard-share-by-good-rule-design-arithmetic">record section 8.3</a>, with each move right independently with chance r; not a measurement. Generator: this page's HTML.</figcaption>
</figure>

Hard is still a pass, but in FSRS each Hard raises the card's difficulty and makes its interval grow less. [Figure 6](#fig-hard-share) shows what would happen if any mistake capped the grade at Hard: at recall 0.9, a 14-move line would be Hard 73% of the time from mistakes alone, against 11% under the decided rule. Long lines would then gather difficulty just for being long.

With Good allowed up to $L(M) - 1$ mistakes, Hard marks a review that is at the limit or slow. On lines of 4 to 7 moves the two rules are the same, because their Good limit is 0; on lines of 3 moves no mistake is allowed at all. Lines of 3 to 7 moves are 79.6% of the catalog, so for most lines the decided rule still means "any mistake gives at most Hard". The figure counts only Hard grades caused by mistakes; slow reviews add more Hard grades, equally under both rules ([record section 7.4](docs.topics.session-grading.session-grading.md.html#74-good-allows-mistakes-below-the-limit)).

</section>

<section class="card" id="app">

## The app's relearn prompts and its hint stay as they are

<p class="bs-lead">The rule fits the current Repeating screen: the prompts after 2 and 4 wrong attempts stay, choosing to relearn saves the review as Again, and copying the hint never enters the time.</p>

<figure id="fig-relearn">
<div class="bs-flow" role="img" aria-label="During a review each wrong attempt is taken back, and the hint shows the expected move once after the first mistake. After 2 wrong attempts the player may continue or relearn; after 4 the only option is relearning. Choosing to relearn abandons the review and saves it as Again. A finished review is graded by the rule.">
<div class="bs-node bs-violet"><span class="bs-label">During the review</span><b>Wrong attempts</b><p>Each wrong attempt is taken back. After the first mistake the app shows the expected move once.</p></div>
<div class="bs-arrow"><span>prompts</span></div>
<div class="bs-stack"><div class="bs-part bs-orange"><span class="bs-label">After 2 wrong attempts</span><p>Continue or relearn.</p></div><div class="bs-part bs-orange"><span class="bs-label">After 4 wrong attempts</span><p>Relearning is the only option.</p></div></div>
<div class="bs-arrow"><span>outcome</span></div>
<div class="bs-stack"><div class="bs-part bs-red"><span class="bs-label">Relearn</span><p>The review is abandoned and saved as Again.</p></div><div class="bs-part bs-teal"><span class="bs-label">Finish the line</span><p>The review is graded by the rule.</p></div></div>
</div>
<figcaption><strong>Figure 7.</strong> The Repeating screen's prompts and the two ways a review ends, from <a href="docs.topics.session-grading.session-grading.md.html#4-interaction-with-the-apps-repeating-screen">record section 4</a>. Arrows show what the player sees in order. Generator: this page's HTML.</figcaption>
</figure>

[Figure 7](#fig-relearn) shows the two ways a review ends. Choosing to relearn is the player saying they do not remember the line, so Again is correct even when the mistakes would have been within the limit.

The prompts count wrong **attempts**; the rule counts **moves** whose first attempt was wrong. Several wrong attempts on one move are one mistake for the grade but several for the prompt. The two never conflict: a finished review keeps its graded result, and an abandoned one is Again.

The hint does not affect the time either. A move with a mistake is not timed, so the time spent copying the expected move never enters $\bar{T}$. Whether the hint stays is a separate product decision of the [App & Practice record](docs.topics.app-practice.app-practice.md.html); the rule does not depend on it.

The rule grades unassisted Repeating reviews only. Grading of guided Learning sessions is not covered and is [still open](#next).

</section>

<section class="card" id="next">

## The app and the simulator run the rule; the app's weights, four questions and the time calibration remain open

<p class="bs-lead">The simulator and the app changed in commit <code>52e9535</code>. The move-recall change then switched the hidden truth and retrained on regenerated data; the app's weights are a team decision, and the time values wait for checks against real browser times.</p>

<div class="bs-checks">
<div class="bs-check"><span class="bs-badge bs-ok">Done</span><h3>Simulator</h3><p>A new grading function from per-move data replaces the old one. A lapse is now "graded Again" instead of "any mistake". The test vectors replace the old threshold tests.</p></div>
<div class="bs-check"><span class="bs-badge bs-ok">Done</span><h3>Training and evaluation</h3><p>A pass is still a grade above Again, but it now means "mistakes within the limit" instead of "no mistakes". The hidden truth is now the chance of passing under the limit.</p></div>
<div class="bs-check"><span class="bs-badge bs-ok">Done</span><h3>App</h3><p>The browser times each move and sends the time with it. The backend grades with the new rule, without a baseline, and the result screen explains each grade from its mistakes and pace.</p></div>
<div class="bs-check"><span class="bs-badge bs-ok">Done</span><h3>Data and pages</h3><p>The move-recall experiment regenerated the synthetic data and retrained the weights; existing experiments stay as results of the earlier rule. Exporting the grading inputs is still open. Pages describing the grade are updated.</p></div>
</div>

The hidden truth for the new pass is the chance of at most $L(M)$ mistakes when each move is recalled with chance $R$, instead of the chance $R^M$ of a clean line:

$$p_{\text{pass}} = \sum_{k=0}^{L(M)} \binom{M}{k} (1-R)^k R^{M-k}$$

[Record section 5](docs.topics.session-grading.session-grading.md.html#5-implementation-targets) names the exact files, functions and constants for each change.

<div class="bs-board">
<div class="bs-row"><span class="bs-state bs-wait">Open</span><b>Memory after a passed review with mistakes</b><span>Both hidden memory models treat any mistake as a lapse, but such a review can now be Hard or Good. Options: count it as a success with the grade's update, or as a reduced success for multiplicative memory. The practice count needs the same decision. For now, without a decision, the simulator counts it as a success but still lowers the practice count.</span></div>
<div class="bs-row"><span class="bs-state bs-wait">Open</span><b>Guided Learning sessions</b><span>Whether they use the time bands, a fixed grade or no grade is not decided. For now the simulator grades them by the time bands, with no mistakes.</span></div>
<div class="bs-row"><span class="bs-state bs-wait">Open</span><b>Grading inputs in the export</b><span>The session CSV has neither \(M\), \(k\) nor \(\bar{T}\), so a dataset cannot be regraded from it. Adding them is recommended, not decided.</span></div>
<div class="bs-row"><span class="bs-state bs-wait">Open</span><b>Time values</b><span>1500, 3500, 8000 and 20000 ms await the checks below.</span></div>
<div class="bs-row"><span class="bs-state bs-ok">Decided</span><b>One pause on 3-move lines</b><span>Accepted as real struggle on a short line; see vector 3 under <a href="#grades">worked examples</a>.</span></div>
</div>

### How the time values will be checked

<div class="bs-part bs-teal"><span class="bs-label">Validation plan, not run</span><ol>
<li><b>Simulation.</b> After the simulator and training changes, check that FSRS's predicted pass chance matches the observed pass rate for short (3–5), medium (6–9) and long (10+) lines, and that long lines do not build up more difficulty than short ones.</li>
<li><b>The Easy boundary from the physical floor.</b> Once the app stores browser times, estimate the fastest a move can be played from the fastest first-try correct moves, for example the 5th percentile, and check that 1500 ms leaves a margin for recognition above it.</li>
<li><b>The Slow and Very slow boundaries from the next review.</b> Check that reviews above each boundary are followed by more mistakes at the line's next review; move a boundary to where that failure rate clearly rises.</li>
<li><b>Device check.</b> Compare how often mouse and touch players land in each band. If touch players rarely reach Fast, the Easy boundary measures the device, not the memory.</li>
</ol></div>

The simulator cannot set the time values: its times come from modelled players, not real ones ([record section 9](docs.topics.session-grading.session-grading.md.html#9-validation-plan)).

The record was written from the code at commit `d69e01d`, inspected on 2026-11-16. The only run was the arithmetic script behind Figures 2 and 6; no simulation, training, app session or human measurement was done ([record section 10](docs.topics.session-grading.session-grading.md.html#10-source-coverage-and-verification-limits)). [Review data & grading](review-dataset.html#grading) keeps the session export's grading inputs and the synthetic evidence gathered before the decision; [System architecture](system-architecture.html#practice) explains the grading path the app runs today.

</section>
