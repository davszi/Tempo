+++
toc = []
title = "Synthetic Clients: Simulating Human Opening Review"
slug = "synthetic-clients"
brand_sub = "cognitive modeling · spaced repetition · latency generation"
components = ["toc", "nav", "code", "filelinks"]
page_css = ["build-sheet.css"]
math = true
+++

# Synthetic Clients: Simulating Human Opening Review

<section class="card" id="overview">

## 1. Overview & Purpose

<p class="bs-lead">Synthetic clients generate realistic chess opening practice logs to train and evaluate TEMPO's Review Planner and FSRS scheduler before human testing begins.</p>

To train our machine learning models, we cannot wait for human players to log thousands of opening reviews over months. Synthetic clients act as digital test subjects with customizable cognitive traits, producing dual-signal session logs:
- **Move Accuracy:** Did the client recall the exact repertoire move?
- **Hesitation Latency:** How many milliseconds did the client spend searching their memory or calculating?

</section>

<section class="card" id="hesitation-model">

## 2. The Hesitation Latency Engine

<p class="bs-lead">Reaction time is not uniform: it combines physical interface latency, log-normal cognitive delay, and exponential strain from memory decay.</p>

```python
# 1. Sample raw hesitation from log-normal distribution (seconds)
raw_hesitation = lognormal(mu, sigma)

# 2. Cognitive strain amplifies hesitation when retrievability R is low
cognitive_strain = np.exp(beta * (1 - R))

# 3. Practice multiplier compresses hesitation as familiarity builds
m_practice = 1.0 / (1.0 + alpha * reps)

# 4. Total cognitive hesitation in milliseconds
total_hesitation_ms = (raw_hesitation * 1000) * cognitive_strain * m_practice

# 5. Final move latency including motor baseline
final_time_ms = baseline_ms + total_hesitation_ms
```

### Cognitive Components:

1. **Physical Baseline ($\text{baseline\_ms}$):**
   The minimum physiological time required to see the position, process visual features, and move the piece on the board (typically 200–400 ms).
2. **Raw Cognitive Hesitation ($\mu, \sigma$):**
   Drawn from a log-normal distribution, accurately reflecting human response times with a steep rise and an extended right-skewed tail.
3. **Cognitive Strain ($\beta$ and $R$):**
   When an opening line is fresh in memory ($R \approx 1.0$), retrieval is effortless ($\text{strain} \to 1.0$). When retrievability drops, the client spends cognitive effort $\beta$ struggling to remember or calculate.
4. **Practice Decay ($m_{\text{practice}}$ and $\alpha$):**
   With each review, the line becomes more automatic. As repetitions grow, $m_{\text{practice}} \to 0$, causing hesitation to approach pure physical baseline.

</section>

<section class="card" id="memory-dynamics">

## 3. Memory & Lapse Dynamics

<p class="bs-lead">Accuracy is governed by memory retrievability, while mistakes trigger a realistic setback in familiarity.</p>

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

A soft penalty reflects the psychological reality that a blunder damages confidence and increases future hesitation without wiping out physical familiarity entirely.

</section>

<section class="card" id="archetypes">

## 4. Benchmark Personas for Demo

<p class="bs-lead">Three initial archetypes provide varied training dynamics for the review planner.</p>

<div class="slide-main">
  <div class="slide-row">
    <div class="slide-tile">
      <h4>The Impulsive Blitzer</h4>
      <p>Low baseline (220 ms), low effort ($\beta = 0.4$), fast decay ($C = 0.65$). Moves fast, hesitates little even when uncertain, but blunders when lines are neglected.</p>
    </div>
    <div class="slide-tile is-term">
      <h4>The Balanced Learner</h4>
      <p>Standard baseline (300 ms), moderate effort ($\beta = 1.0$), average decay ($C = 0.50$). Representative baseline for general benchmark evaluation.</p>
    </div>
    <div class="slide-tile">
      <h4>The Diligent Calculator</h4>
      <p>High baseline (380 ms), high effort ($\beta = 2.2$), strong retention ($C = 0.35$). Takes significant time when retention dips, building high automaticity through practice.</p>
    </div>
  </div>
</div>

</section>
