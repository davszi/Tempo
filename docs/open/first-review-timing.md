# Proposal: first review the next day, same-day practice off the schedule

Status: open proposal, not accepted. Written on 2026-11-17 at the user's
request after a discussion of FSRS learning steps. The user ruled out
letting a Learning session set a line's starting memory. No app, simulator
or training change has been made. The simulator and training changes are
deliberately deferred: the user asked for them not to be done yet.

## What is verified

Source inspected at `cf7b7be`, runtime weights at `fd3fe89`:

- **The runtime scheduler has no learning steps.** `MLEngine` builds its
  py-fsrs `Scheduler` with `learning_steps=()` and `relearning_steps=()`
  ([`backend/ml_engine.py`](../../backend/ml_engine.py), `from_weights_file`
  and `__init__`). A new card's first review moves it straight into FSRS's
  Review state.
- **Learning sends nothing to FSRS.** When a Learning session completes,
  `PracticeController.submit_move` calls `MLController.initialize_progress`
  ([`backend/practice_controller.py`](../../backend/practice_controller.py),
  [`backend/ml_controller.py`](../../backend/ml_controller.py)). It stores
  `MLEngine.initial_schedule(now)`: an empty `Card(due=now)`, so the line is
  due at once with no stability or difficulty.
- **The first Repeating review sets the starting memory.** In py-fsrs
  `review_card`, a card with no stability takes stability `w[G−1]` and
  starting difficulty `w4 − e^(w5·(G−1)) + 1` from the review's grade `G`,
  however soon after the lesson the review happens.
- **The planner serves the longest-overdue line first.** `select_line`
  picks the due line with the earliest `next_review_at`, so a line due
  "now" waits behind lines that were already overdue.
- **Since `42a6810`, the lesson-complete "Review without hints" button runs
  an unguided Learning session**, not a Repeating review
  ([`frontend/src/components/LessonPage.tsx`](../../frontend/src/components/LessonPage.tsx)).
  It does not add to the repertoire or reach FSRS.

Design arithmetic, not a measurement: at the scheduler's desired retention
of 0.9, the py-fsrs interval equals the stability in days, rounded and at
least one day. Since `fd3fe89` the runtime weights in
[`backend/fitted_global.csv`](../../backend/fitted_global.csv) are the
per-move A1c-pass fit of seed 20261111 from the
[move-recall experiment](../../ml/experiments/2026-11-16-move-recall/SUMMARY.md)
(`w0 = 0.212`, `w1 = 1.2931`, `w2 = 2.01454`, `w3 = 9.681611`; identical to
`results/seed-20261111/A1c-pass/fsrs6_general_parameters.json`). With them, a
first review graded Again or Hard is next due after 1 day, Good after 2 days
and Easy after 10 days. The line-level weights before `fd3fe89`
(`w2 = 2.2400`, `w3 = 8.2956`) gave 2 and 8 days. The scheduler still uses
line-level recall, which the
[move recall record](../topics/move-recall/move-recall.md) says should not be
combined with per-move weights; that question is separate from this proposal.

## The problem from the player's side

This section is reasoning about how people learn a line. It has not been
measured with TEMPO players.

1. In the guided lesson the player follows arrows: they see the moves but
   have not yet produced them unaided.
2. Straight after the lesson the line is still in short-term memory. Playing
   it without hints feels good and helps the memory settle, but almost
   everyone passes, often quickly. Such a test says little about whether the
   line will last.
3. After a night's sleep the line is either in long-term memory or it is
   not. A review then is the first honest measure of whether it was learned.
4. From then on, spaced reviews at growing intervals do the work FSRS is
   built for.

Today the first review usually comes in step 2. The decided
[session grading rule](../topics/session-grading/session-grading.md) can
grade a clean, quick run Easy, which by the arithmetic above schedules the
next review 10 days later. By then much of a line learned the same day may be
gone; the player fails, the line drops to Again, and their first experience
of Repeating is "I thought I knew this." The schedule took a test of
short-term memory as proof that the line had stuck.

## Proposal

| Moment | What the player does | What FSRS does |
|---|---|---|
| End of the lesson | Optional "Practise without hints": the unguided Learning session that already exists since `42a6810` | Nothing; logged as practice, not as a review |
| Rest of the same day | Can repeat that practice as often as they like | Nothing |
| The next day | The line's first Repeating review, chosen by the planner | This review sets the starting memory (`w0`–`w3`, starting difficulty) |
| After that | Normal Repeating | Normal FSRS scheduling |

- **Same-day review: yes, as practice the player chooses**, not as an FSRS
  learning step. The player gets to test themselves; the schedule is not
  fooled by short-term memory.
- **First review: the next day.** It is the first review that says something
  about long-term memory, so it is the right one to set the starting memory.
  Learning still sets nothing, as the user asked.
- **Settled rules stay intact.** Same-day practice is a Learning session, where
  the player chooses the line; every Repeating review is still the planner's
  choice ([project context, section 9](../PROJECT_CONTEXT.md#9-the-earlier-prototype)).
  This does not resolve the separate selected-line review and hint
  deviations owned by [App & Practice](../topics/app-practice/app-practice.md#unresolved-repeating-behavior).
- **A failed first review is handled naturally.** Again gives the low starting
  stability `w0`, so the line comes back the next day.

## Changes it would need

Prospective; none is made.

- **Backend:** `MLEngine.initial_schedule` returns a first due time on the
  next day instead of `now`. The card stays empty, so the first Repeating
  review still initializes it.
- **Frontend:** the lesson-complete screen says when the first review is
  ("First review tomorrow") and offers same-day practice, so the wait reads
  as planned. Repertoire and schedule screens show the line as learned, not
  due.
- **Telemetry:** decide whether same-day practice gets its own logged event
  so it can be analysed later without touching the schedule.
- **Simulator and training (deferred by the user):** the simulator currently
  gives each new line a Learning session that sets its memory and a
  Repeating session a few minutes later
  ([`ml/tempo_ml/simulator/practice.py`](../../ml/tempo_ml/simulator/practice.py),
  [session grading 6.2](../topics/session-grading/session-grading.md#62-guided-learning-sessions)).
  Matching this proposal means: learning may still change the simulator's
  hidden memory, but the generated history shows only ungraded practice on
  the learning day and the first graded review on a later day; then the
  datasets are regenerated and the weights retrained. Until that is done,
  the trained weights assume a different first-review pattern from the app.

## Alternatives considered

- **py-fsrs learning steps** (reviews minutes apart before the card enters
  Review): rejected. A TEMPO review is a whole line, not a flashcard, and the
  player may leave between sessions; steps would also make the schedule
  push the same line again within minutes and would grade guided play as
  recall.
- **Let the Learning session set the starting memory and keep the immediate
  review as a same-day update:** closest to the current simulator, but ruled
  out by the user, and a guided lesson does not test recall.
- **Keep today's behavior:** the starting memory keeps coming from a
  short-term test, with the long first intervals described above.

## Open questions

1. What "the next day" means: the next calendar day in the player's time
   zone (the backend currently stores UTC times) or a minimum number of
   hours after the lesson.
2. Whether a failed same-day practice should do anything, such as offering
   the lesson again. The proposal keeps it off the schedule either way.
3. Whether same-day practice is logged as its own event type.
4. When the simulator and training follow, and whether the app change waits
   for retrained weights or ships first with the mismatch noted.

Closure: the team accepts, changes or rejects the proposal. If accepted, the
decision moves into the App & Practice and System Architecture records, the
backend and frontend changes land with their checks, and the simulator and
training follow-up gets its own route.
