# Session Grading

## 1. Scope and status

This record is the canonical specification of the **session grading
function**: the rule that turns one finished Repeating Mode review of a line
into an FSRS grade (1 Again, 2 Hard, 3 Good, 4 Easy).

| Item | Owner |
|---|---|
| Grading specification, decisions, rationale, implementation targets | this record |
| Human explanation | [`index.md`](index.md) |
| Session export columns and the earlier synthetic evidence | [Review dataset record](../review-dataset/record.md), sections 2 and 3 |
| Runtime grading path in the app | [System architecture record](../system-architecture/system-architecture.md#initial-card-grading-and-update) |
| Browser timing and Repeating screens | [App & Practice record](../app-practice/app-practice.md) |
| Synthetic move times and hidden memory | [Synthetic-client record](../synthetic-clients/record.md) |
| Pass label and fitting | [FSRS training record](../fsrs-training/fsrs-training.md) |

**Status (2026-11-16): decided, not implemented.** The rule in section 3 was
decided in the 2026-11-16 grading discussion. The simulator
(`ml/tempo_ml/simulator/grading.py`) and the app (`backend/ml_engine.py`)
still apply the earlier rule (section 7.1). Every recorded synthetic dataset
and trained weight was graded with the earlier rule. Section 5 lists the
implementation work; section 6 lists what is still open.

The time boundaries in section 3.4 are **starting values chosen from
published orders of magnitude, not calibrated against human data**
(section 8.4). Section 9 says how to check them once the app records
browser times.

## 2. Terms

| Term | Definition |
|---|---|
| Review | One Repeating Mode session on one line, played to the end. A wrong move is taken back and retried until it is right. |
| `M` | Number of moves the **player** plays in the line (the player's side only; every ply when the side is Both). |
| Mistake | A player move whose **first** attempt was wrong. Further wrong attempts on the same move do not add mistakes. |
| `k` | Number of mistakes in the review, `0 ≤ k ≤ M`. |
| Accuracy | `(M − k) / M`. Shown to people; the rule uses `k` and `M`, not this share. |
| Mistake limit `L(M)` | The most mistakes a review of a line of length `M` may have without being Again (section 3.2). |
| Good limit `G(M)` | `max(0, L(M) − 1)`: the most mistakes a review may have and still be Good. |
| Timed move | A player move that was right on its first attempt and is not the line's first player move. |
| Move time | Browser-measured time from the moment the position is ready for the player's move to the moment the player plays it (section 3.3). |
| `T̄` | Mean of the capped move times of the timed moves (section 3.3). |
| Time band | Fast, Normal, Slow or Very slow, from `T̄` (section 3.4). |

## 3. The decided rule

### 3.1 Inputs and output

The function receives, for one finished review:

- `M`, the line's player move count;
- for each player move: whether its first attempt was right, and its
  browser-measured time of the first attempt in milliseconds.

It returns one grade: 1 Again, 2 Hard, 3 Good or 4 Easy. It optimizes
nothing and has no per-player parameters. There is no physical baseline:
nothing is subtracted from any time.

### 3.2 Mistake limits by line length

| Line length `M` | Mistake limit `L(M)` | Good limit `G(M)` | Catalog lines |
|---|---|---|---|
| 3 or fewer | 0 | 0 | 164 (6.0%) |
| 4–7 | 1 | 0 | 2,000 (73.6%) |
| 8–12 | 2 | 1 | 528 (19.4%) |
| 13 or more | 3 | 2 | 27 (1.0%) |

Catalog counts are measured (section 8.1). The largest limit is 3, below the
4 wrong attempts at which the app already forces a relearn (section 4.2).

### 3.3 Measuring the time

1. Measure each move time **in the browser**: start when the position with
   the player to move is shown (after the opponent's reply has been drawn),
   stop when the player's move is made (drop or second click). Do not use
   server receipt times; they include network and rendering time.
2. Keep only **timed moves**: drop every move with a mistake, and drop the
   line's first player move (it includes orienting to the board).
3. **Cap** each timed move's time at `CAP_MS = 20000`.
4. `T̄` = mean of the capped times of the timed moves.
5. If there are no timed moves, the time band is Normal.

Retry attempts and hint-copying time never enter `T̄`; mistakes are counted
once, in `k`.

### 3.4 Time bands

| Constant | Value |
|---|---|
| `T_EASY_MS` | 1500 |
| `T_SLOW_MS` | 3500 |
| `T_VERY_SLOW_MS` | 8000 |
| `CAP_MS` | 20000 |

| Band | Condition |
|---|---|
| Fast | `T̄ < 1500` |
| Normal | `1500 ≤ T̄ ≤ 3500` |
| Slow | `3500 < T̄ ≤ 8000` |
| Very slow | `T̄ > 8000` |

Meaning of each boundary:

- `T_EASY_MS`: below it the line was played from recognition; the time is
  mostly the physical move.
- `T_SLOW_MS`: above it the player had to think. It only lowers reviews
  **with** mistakes below the limit (Good → Hard).
- `T_VERY_SLOW_MS`: above it the player worked the line out rather than
  remembered it. It is the only time that lowers a review **without**
  mistakes (Good → Hard).
- `CAP_MS`: stops one interruption from deciding the band.

### 3.5 Decision procedure

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

Easy requires `k == 0`. A review with mistakes is never Easy.

### 3.6 Full grade table

| Line length | Mistakes `k` | Accuracy | Fast | Normal | Slow | Very slow |
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

The accuracy column is the range over the catalog lengths in each band
(13 or more: the 13- and 14-move lines). It is explanatory only.

### 3.7 Test vectors

Times are listed per player move in order; `x` marks a move with a mistake
(its time is ignored). The first move is never timed.

| # | `M` | Move times (ms) | `k` | `T̄` (ms) | Band | Grade |
|---|---|---|---|---|---|---|
| 1 | 3 | 5000, 900, 1100 | 0 | 1000 | Fast | Easy |
| 2 | 3 | 900, 900, x | 1 | — | — | Again |
| 3 | 3 | 900, 20000, 1000 | 0 | 10500 | Very slow | Hard |
| 4 | 4 | 900, 20000, 1000, 1000 | 0 | 7333 | Slow | Good |
| 5 | 5 | 900, 2000, 2500, 3000, 2600 | 0 | 2525 | Normal | Good |
| 6 | 6 | 900, 1000, x, 1200, 1100, 1300 | 1 | 1150 | Fast | Hard |
| 7 | 6 | 900, x, x, 1000, 1000, 1000 | 2 | 1000 | Fast | Again |
| 8 | 10 | 900, x, 1000 ×8 | 1 | 1000 | Fast | Good |
| 9 | 10 | 900, x, 4000 ×8 | 1 | 4000 | Slow | Hard |
| 10 | 10 | 900, x, x, 1000 ×7 | 2 | 1000 | Fast | Hard |
| 11 | 13 | 900, x, x, 2000 ×10 | 2 | 2000 | Normal | Good |
| 12 | 13 | 900, x, x, x, 2000 ×9 | 3 | 2000 | Normal | Hard |
| 13 | 8 | 900, 9000 ×7 | 0 | 9000 | Very slow | Hard |
| 14 | 8 | 900, 30000, 1000 ×6 | 0 | 3714 | Slow | Good |

Vector 14 shows the cap: 30000 counts as 20000, giving
`(20000 + 6 × 1000) / 7 ≈ 3714`. Vector 4 shows that from 4 moves up a
single capped pause cannot make a review without mistakes Very slow;
vector 3 shows that on a 3-move line it can (section 6.4).

## 4. Interaction with the app's Repeating screen

### 4.1 Hint after the first mistake

The current app shows the expected move once after the first mistake
(`frontend/src/components/LessonPage.tsx`, `wrongMove`). Because mistaken
moves are not timed (section 3.3), copying the hint does not affect `T̄`.
Whether the hint stays is a separate product decision owned by the
[App & Practice record](../app-practice/app-practice.md); this rule does
not depend on it.

### 4.2 Relearn prompts stay unchanged

Decided: the app keeps its prompts. After 2 wrong attempts the player may
continue or relearn; after 4 the only option is relearning. Choosing to
relearn abandons the review and saves it as Again
(`practiceRequest("review/abandon")`). This is the player reporting that
they do not remember the line, so Again is correct even when `k` would be
within the limit.

The prompts count wrong **attempts**; the rule counts **moves** with a
wrong first attempt (section 2). Several wrong attempts on one move are one
mistake for grading but several for the prompt. No conflict arises: a
completed review with `k ≤ 3` keeps its graded result, and an abandoned
review is Again.

### 4.3 Scope

The rule grades unassisted Repeating reviews only. Grading guided Learning
sessions is not covered (section 6.2).

## 5. Implementation targets

Not started. Implement as one change across the simulator, the app and the
documentation, then regenerate data (section 5.4).

### 5.1 Simulator (`ml/tempo_ml/simulator/`)

1. `grading.py`: replace `calculate_session_grade(blunder_count,
   total_time_ms, num_moves, baseline_ms)` with a function implementing
   section 3. Inputs: `M`, per-move first-attempt correctness and per-move
   first-attempt time. Remove `EASY_MAX_DELAY_MS`, `GOOD_MAX_DELAY_MS` and
   the baseline argument; add the four constants of section 3.4 and the
   mistake-limit table of section 3.2.
2. `clients.py` (`_finish` and the Repeating path near the current
   `calculate_session_grade` calls): pass per-move data. Simulated move
   times include `baseline_ms` as part of the physical move; keep it in the
   time, do not subtract it.
3. Lapse handling: `clients.py` treats any blunder as a lapse
   (`blundered = any(...)`, `after_lapse`, `last_review_lapsed`,
   `next_reps(..., blundered=...)`). Switch the lapse condition to
   `grade == AGAIN`. The memory update for a non-Again review with
   mistakes is open (section 6.1).
4. Guided sessions currently go through the same grading call with no
   mistakes; keep that path working (section 6.2).
5. Tests in `ml/tests/test_simulator.py`: replace the old threshold tests
   with the vectors of section 3.7.

### 5.2 Training and evaluation (`ml/tempo_ml/fsrs/`, `ml/tempo_ml/evaluate/`)

1. The pass label stays `grade > 1` (`fsrs/model.py`, `load_cards`), but its
   meaning changes from "no mistakes" to "mistakes within `L(M)`". Update
   the module docstring that says the line was played without a blunder.
2. Hidden truth: `generate.py` writes `p_clean = R^M` for Repeating rows.
   The matching truth for the new pass label is the chance of at most
   `L(M)` mistakes:
   `p_pass = Σ_{k=0..L(M)} C(M,k) (1−R)^k R^(M−k)`.
   Decide whether to rename the column or add `p_pass` beside `p_clean`;
   the `--target true` diagnostic and `evaluate/metrics.py` `Truth` must
   read the chosen column.

### 5.3 App (`backend/`, `frontend/`)

1. Browser timing: measure each attempt's time in `LessonPage.tsx` as in
   section 3.3 and send it with the move request; the backend stores it in
   `practice_events.response_time_ms` instead of the server interval from
   `practice_controller.py` (`elapsed_ms`). The API change belongs to the
   App & Practice record. Decide how the server treats a missing or
   implausible client time.
2. `backend/ml_engine.py` `grade_session(attempts, baseline_ms)`: implement
   section 3 from the stored attempts. `M` is the number of distinct
   `move_index` values; `k` is the number of those whose first attempt
   (lowest `event_id`) is wrong; the first player move is the smallest
   `move_index`. Remove the `baseline_ms` parameter and its constructor
   argument.
3. `LessonPage.tsx` grade explanations (`gradeReason` and the result text
   "Any mistake means Again") must describe the new rule.
4. Keep the relearn prompts and the abandon-as-Again path (section 4.2).

### 5.4 Data and documentation

1. Regenerate synthetic datasets and retrain weights; record them as new
   dated experiments. Existing experiments stay as historical results of
   the earlier rule.
2. Update the review dataset record section 3, the system architecture
   record's grading paragraph and the pages that explain them, so that they
   describe the implemented rule.
3. Consider exporting `M`, `k` and `T̄` (or per-move times) in the session
   CSV so grades can be recomputed if boundaries change (section 6.3).

## 6. Open items

Items 6.1–6.3 and 6.5 are open. Item 6.4 is a trade-off accepted on
2026-11-16, kept here because it qualifies `CAP_MS`.

### 6.1 Memory update for a passed review with mistakes

Both hidden memory models treat any blunder as a lapse
(synthetic-client record, section 7). Under this rule a review with
mistakes can be Hard or Good. Options: (a) treat it as a success with the
grade's update (FSRS memory already does this by grade; multiplicative
memory has no grade input); (b) a reduced success for multiplicative
memory. The `reps` rule (+1 clean, −2 blunder) needs the same decision.

### 6.2 Guided Learning sessions

The simulator grades guided sessions by latency with perfect accuracy; they
update state but are excluded from the training loss. Whether they use the
section 3.4 bands, a fixed grade or no grade is not decided.

### 6.3 Exported inputs

The seven-column session export has neither `M` nor `k` nor `T̄`, so a
dataset cannot be regraded from the CSV alone. Adding them is recommended,
not decided.

### 6.4 One pause on 3-move lines

A 3-move line has two timed moves, so one capped pause (20000 ms) plus one
quick move gives `T̄ = 10500`, Very slow, Hard (test vector 3). From 4 moves
up this cannot happen. Accepted on 2026-11-16 as real struggle on a short
line; lowering `CAP_MS` to 15000 would remove it at the cost of a weaker
time signal on every line.

### 6.5 Calibration of the time constants

The section 3.4 values await the checks of section 9.

## 7. Decisions and rationale

All decided 2026-11-16 unless marked.

### 7.1 Earlier rule, superseded

Implemented in the simulator and the app until section 5 lands: any mistake
gives Again; otherwise `total_time_ms / M − baseline_ms` gives Easy below
500 ms, Good from 500 to 1,800 ms, Hard above 1,800 ms. The app's baseline
is 0 and its time is server-measured.

### 7.2 Grade from mistakes and time

The two signals are recall (mistakes) and fluency (time). No third signal
is added. Rejected additions: mistake severity (inaccuracy/blunder), because
the project relies on a move being simply right or wrong and the planner is
meant to stay general; position-weighted mistakes for shared opening
prefixes, deferred as a larger change.

### 7.3 Mistake limits by length, not one accuracy share

Rationale: a fixed share is harsh on short lines (a 3-move line can only
reach 100%, 67%, 33% or 0%) and, on long lines, turns Again into a cliff at
the boundary; a fixed count is harsh on long lines (section 8.2). Within
the catalog's 3–14 moves an 80% share already reduces to whole-mistake
limits, so a table is simpler to explain. Compared candidates: any mistake;
0/1/2 by 3 | 4–9 | 10+; accuracy below 70%; and the decided 0/1/2/3 by
3 | 4–7 | 8–12 | 13+. The decided table is the most even across lengths
(Again 3–15% for 4–14 moves at 90% per-move recall), averages about the
10% failure rate a 0.9 desired retention expects, still separates
remembering from forgetting (9.5% → 29.4% Again as per-move recall falls
from 0.9 to 0.8), and never allows 4 mistakes. "Accuracy below 70%" was
rejected: it allows 4 mistakes on 14-move lines, clashing with the forced
relearn, and is too lenient on long lines.

### 7.4 Good allows mistakes below the limit

Rationale: Hard is a pass, but in FSRS each Hard raises the card's
difficulty and grows its interval less. If any mistake capped a review at
Hard, a player who knows a long line well would still get Hard most of the
time from chance slips (section 8.3), so long lines would accumulate
difficulty twice for their length. With Good allowed up to `L(M) − 1`, Hard
marks a review at the limit or a slow one. On 3–7 move lines (80% of the
catalog) this equals "any mistake gives at most Hard".

### 7.5 Easy requires no mistakes

Decided directly.

### 7.6 Slow without mistakes stays Good; Very slow gives Hard

A review without mistakes but Slow is Good: correct recall is not graded as
a struggle because of a slow device or slow hands. A separate, generous
Very slow boundary still gives Hard, as a safety net for clear struggle.
Reviews with mistakes below the limit keep the stricter Slow boundary.
Alternative considered: one shared slow boundary for both cases (fewer
constants); not taken, the decided rule keeps both.

### 7.7 Time only first-try correct moves, capped, browser-measured, first move excluded

- First-try correct only: keeps accuracy and time independent; retries and
  hint copying would otherwise count a mistake twice.
- Cap: one interruption (notification, tab switch) must not decide the
  grade; capping observed times is standard in latency-based learning
  systems (section 8.4).
- Browser timing: server intervals add network round trips and rendering to
  every move, a device- and connection-dependent offset.
- First move excluded: its time includes taking in the board.

### 7.8 Fixed time constants, no baseline, no per-player pace

Decided: fixed values for every player. Rationale: there is a time in which
a known opening move should be playable on any device. Alternative not
taken: comparing with each player's own typical pace (as SlimStampen does,
section 8.4). Consequence accepted: slower hands or devices reach Easy
less often. The earlier baseline subtraction stays removed because the app
cannot know a player's baseline.

### 7.9 Relearn prompts unchanged

See section 4.2.

## 8. Evidence

### 8.1 Catalog line lengths (measured)

Player moves per line in `backend/tempo_demo.sqlite` at commit `d69e01d`,
measured 2026-11-16 with Python 3.13.5 by
[`evidence/2026-11-16-grading-arithmetic/grading_arithmetic.py`](evidence/2026-11-16-grading-arithmetic/grading_arithmetic.py)
(`python -I docs/topics/session-grading/evidence/2026-11-16-grading-arithmetic/grading_arithmetic.py`
from the repository root). White lines count odd plies, Black lines even
plies.

| Moves | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 | 14 | 18 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Lines | 164 | 601 | 574 | 481 | 344 | 218 | 146 | 98 | 45 | 21 | 19 | 7 | 1 |
| Cumulative | 6.0% | 28.1% | 49.2% | 66.9% | 79.6% | 87.6% | 93.0% | 96.6% | 98.2% | 99.0% | 99.7% | 100% | 100% |

Total 2,719 lines.

### 8.2 Again chance by rule (design arithmetic)

Not a simulation or a measurement. Assumes each move is right
independently with probability `r` (binomial); real mistakes probably
cluster after a forgotten branch point. "Catalog avg" weights lengths 3–14
by section 8.1 (2,718 of 2,719 lines). Same script as section 8.1.

Mistake limits per length:

| Rule | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 | 14 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Any mistake | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 0/1/2 (3 \| 4–9 \| 10+) | 0 | 1 | 1 | 1 | 1 | 1 | 1 | 2 | 2 | 2 | 2 | 2 |
| **Decided** 0/1/2/3 (3 \| 4–7 \| 8–12 \| 13+) | 0 | 1 | 1 | 1 | 1 | 2 | 2 | 2 | 2 | 2 | 3 | 3 |
| Accuracy below 70% | 0 | 1 | 1 | 1 | 2 | 2 | 2 | 3 | 3 | 3 | 3 | 4 |

Again chance, `r = 0.9`:

| Rule | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 | 14 | Catalog avg |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Any mistake | 27% | 34% | 41% | 47% | 52% | 57% | 61% | 65% | 69% | 72% | 75% | 77% | 45.4% |
| 0/1/2 | 27% | 5% | 8% | 11% | 15% | 19% | 23% | 7% | 9% | 11% | 13% | 16% | 11.8% |
| **Decided** | 27% | 5% | 8% | 11% | 15% | 4% | 5% | 7% | 9% | 11% | 3% | 4% | 9.5% |
| Accuracy < 70% | 27% | 5% | 8% | 11% | 3% | 4% | 5% | 1% | 2% | 3% | 3% | 1% | 7.6% |

Again chance, `r = 0.8`:

| Rule | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 | 14 | Catalog avg |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Any mistake | 49% | 59% | 67% | 74% | 79% | 83% | 87% | 89% | 91% | 93% | 95% | 96% | 70.9% |
| 0/1/2 | 49% | 18% | 26% | 34% | 42% | 50% | 56% | 32% | 38% | 44% | 50% | 55% | 33.6% |
| **Decided** | 49% | 18% | 26% | 34% | 42% | 20% | 26% | 32% | 38% | 44% | 25% | 30% | 29.4% |
| Accuracy < 70% | 49% | 18% | 26% | 34% | 15% | 20% | 26% | 12% | 16% | 21% | 25% | 13% | 24.6% |

Catalog averages for the decided table at `r` = 0.95 / 0.9 / 0.8 / 0.7:
3.0% / 9.5% / 29.4% / 51.4%.

Known limits of any whole-mistake table: Again drops sharply where the
limit rises (decided table: 15% at 7 moves, 4% at 8, `r = 0.9`); 3-move
lines stay strict (27% at `r = 0.9`).

### 8.3 Hard share by Good rule (design arithmetic)

Share of reviews that are Hard **because of mistakes** under the decided
mistake limits (slow reviews add more Hard, equally under both rules).
Same assumptions and script as section 8.2.

| Rule | `r` | 4 | 7 | 8 | 10 | 12 | 14 |
|---|---|---|---|---|---|---|---|
| Any mistake gives at most Hard | 0.95 | 17% | 26% | 33% | 39% | 44% | 51% |
| **Decided**: Good up to `L(M) − 1` | 0.95 | 17% | 26% | 5% | 7% | 10% | 3% |
| Any mistake gives at most Hard | 0.9 | 29% | 37% | 53% | 58% | 61% | 73% |
| **Decided**: Good up to `L(M) − 1` | 0.9 | 29% | 37% | 15% | 19% | 23% | 11% |

### 8.4 Published research behind the time constants

No source gives cut-offs for this task. The sources support the meaning of
each boundary and its order of magnitude:

| Finding | Source | Used for |
|---|---|---|
| Retrieval latency rises with longer lags and falls after retrieval practice; slow correct answers serve as a difficulty index | [PMC6289840](https://pmc.ncbi.nlm.nih.gov/articles/PMC6289840), [PMC4480221](https://pmc.ncbi.nlm.nih.gov/articles/PMC4480221) | Slow → Hard is grounded |
| SlimStampen raises an item's forgetting rate after slow correct answers, compares with the expected time per learner and item, and caps observed times because interruptions inflate them | [Mindwise Groningen](https://mindwise-groningen.nl/capturing-the-dynamics-of-learning-and-forgetting-through-adaptive-retrieval-practice/), [Sense et al. 2016](https://pubmed.ncbi.nlm.nih.gov/26748838/) | `CAP_MS`; the per-player alternative of 7.8 |
| ARTS spaces by accuracy and response time; one mastery criterion was 4 correct in a row, each under 7 s | [Mettler, Massey & Kellman 2011](https://kellmanlab.psych.ucla.edu/files/mettler_massey_kellman_2011.pdf), [CogSci 2020](https://cognitivesciencesociety.org/cogsci20/papers/0138/index.html) | `T_VERY_SLOW_MS` order of magnitude |
| FSRS uses no response time; an Anki add-on defaults to Easy under 1 s and Hard from 7 s, without justification | [Anki forum](https://forums.ankiweb.net/t/pass-fail-review-automatic-difficulty-rating-based-on-answer-time-beta-ver-official-thread/53872) | Comparable shape, not a source of values |
| Strong players encode chess relations automatically and in parallel | [Reingold et al. 2001](https://link.springer.com/article/10.3758/BF03196185) | Known moves are fast: `T_EASY_MS` |
| Online players think less in the opening than a value-of-computation model predicts, attributed to opening knowledge | [Russek et al. 2025](https://cocosci.princeton.edu/papers/RussekThinking2025.pdf) | Same |
| In 3-minute blitz, about 5 s (the slowest quarter of moves) marks real thinking | [Lichess blog](https://lichess.org/ublog/Kwxe88CS/redirect) | `T_SLOW_MS` below 5 s, since `T̄` is a mean over known moves |
| Pointing takes roughly 0.4–1.3 s per movement; dragging is slower; mouse and touch differ | [MacKenzie et al. 2009](https://yorku.ca/mack/hfes2009.html), [Microsoft Research](https://www.microsoft.com/en-us/research/?p=286148), [Wobbrock et al. 2013](https://faculty.washington.edu/wobbrock/pubs/chi-13.04.pdf) | `T_EASY_MS` leaves room for the physical move |

The constants are spaced by a factor of about 2.3–2.5
(1500 → 3500 → 8000 → 20000), matching the multiplicative spread of
response times.

## 9. Validation plan

Not run. In this order:

1. **Simulation.** After section 5.1–5.2, regrade or regenerate synthetic
   data and check that FSRS's predicted pass chance matches the observed
   pass rate for short (3–5), medium (6–9) and long (10+) lines, and that
   long lines do not accumulate higher difficulty than short ones.
2. **`T_EASY_MS` from the physical floor.** Once the app stores browser
   times, estimate the move floor from the fastest first-try correct moves
   (for example the 5th percentile) and check that `T_EASY_MS` leaves a
   recognition margin above it.
3. **`T_SLOW_MS` and `T_VERY_SLOW_MS` from the next review.** Check that
   reviews above each boundary are followed by more mistakes at the line's
   next review; move a boundary to where that failure rate clearly rises.
4. **Device check.** Compare mouse and touch players' band shares. If touch
   players rarely reach Fast, `T_EASY_MS` measures the device.

The simulator cannot set the time constants: its times come from modelled
players.

## 10. Source coverage and verification limits

Inspected on 2026-11-16 at `d69e01d` by targeted reads and searches, not
full-file audits: `ml/tempo_ml/simulator/grading.py`
(`calculate_session_grade`), `simulator/clients.py` (grading calls, lapse
and `reps` handling), `simulator/memory/multiplicative.py`,
`simulator/generate.py` (`p_clean`), `fsrs/model.py` (`load_cards`, pass
label), `backend/ml_engine.py` (`grade_session`, `schedule_review`),
`backend/practice_controller.py` (`submit_move`, `elapsed_ms`) and
`frontend/src/components/LessonPage.tsx` (`wrongMove`, relearn prompts,
`gradeReason`). Nothing was changed or executed in them. The only run was
the section 8 script. No simulation, training, app session or human
measurement was performed for this record.

## Page presentation and numeric sources

| Displayed numbers or construction | Source |
|---|---|
| Mistake limits 0/1/2/3, Good limits 0/0/1/2, length bands 3 \| 4–7 \| 8–12 \| 13+ | Section 3.2 |
| 1500 / 3500 / 8000 / 20000 ms; band conditions | Section 3.4 |
| Grade table and accuracy ranges | Section 3.6 |
| Test vector values, 10500 and 7333 ms pause examples | Section 3.7 |
| Catalog counts and shares (164, 2,000, 528, 27; 6.0%, 73.6%, 19.4%, 1.0%; 2,719; 79.6% of lines at 7 moves or fewer) | Sections 3.2 and 8.1 |
| 15000 ms alternative cap | Section 6.4 |
| Again chances, catalog averages 9.5% / 29.4% and 3.0% / 51.4% | Section 8.2 |
| Hard shares by Good rule | Section 8.3 |
| 2 and 4 wrong attempts for the relearn prompts | Section 4.2 |
| Research figures (0.4–1.3 s, 5 s, 7 s, 1 s, factor 2.3–2.5) | Section 8.4 |
| Earlier rule 500 / 1,800 ms | Section 7.1 |
