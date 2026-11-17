# Proposal: first review the next day, same-day practice off the schedule

Status: the app part is implemented; the simulator and training part is
open. Written on 2026-11-17 at the user's request after a discussion of
FSRS learning steps. The user ruled out letting a Learning session set a
line's starting memory. Later on 2026-11-17 the user asked for the app
changes to be implemented and chose the next local day starting at 04:00
(open question 1); see [Implemented in the app](#implemented-in-the-app).
The simulator and training changes are deliberately deferred: the user
asked for them not to be done yet.

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

Written before the implementation; the backend and frontend items are now
done as described in [Implemented in the app](#implemented-in-the-app).

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

## Implemented in the app

Implemented on 2026-11-17 at the user's request; the commit hash is in the
[worklog](../worklog.md). The simulator, training and `ml/` code are
unchanged.

- **First due time.** `first_review_due` in
  [`backend/ml_engine.py`](../../backend/ml_engine.py) returns
  `DAY_STARTS_AT_HOUR` (4) local time on the day after the player's learning
  day, in UTC. A day runs from 04:00 to 04:00, as in Anki's day rollover, so
  a line learned at 01:30 is due at 04:00 the same morning.
  `MLEngine.initial_schedule` stores an empty py-fsrs card with that due
  time; Learning still sets no stability or difficulty.
- **Time zone.** The browser sends its IANA zone
  (`Intl.DateTimeFormat().resolvedOptions().timeZone`) as `time_zone` when a
  Learning session starts (`/api/learning`). `player_zone` turns it into a
  `ZoneInfo`, uses UTC when it is missing and refuses an unknown name before
  the lesson opens. `tzdata` is declared in `backend/requirements.txt`
  because Windows has no system time zone database.
- **No early first review.** `PracticeController.start_review_line` refuses
  a chosen-line review of a line that has no stability and is not yet due.
  In the browser, `startReview` sends such a line to an unguided Learning
  session ("Practise without hints") with a message saying when the first
  review opens, so every per-line Review or Practise button behaves the same.
  Lines that have had their first review keep the existing chosen-line
  behavior, which [App & Practice](../topics/app-practice/app-practice.md#unresolved-repeating-behavior)
  still owns.
- **Screens.** The lesson-complete screen says "First review tomorrow from
  04:00, once it has had a night to settle" (local time format) and labels its
  button "Practise without hints"; a finished practice says it does not
  change the schedule. The repertoire chip of an untested line reads "First
  test tomorrow" (or "later today") until the line is due, then "First test
  ready".
- **Terminal demo.** `backend/demo.py` checks that nothing is due right after
  learning, then moves its clock to the first due time before reviewing.

Checks on 2026-11-17: `python -m unittest discover -s backend/tests -t .`
passes 36 of 36, including 14 new tests in `backend/tests/test_first_review.py`
(due-time cases for evening, morning, 04:00, after midnight, a UTC-day
difference and a daylight-saving change; the stored card; no review the same
day; refused early chosen-line review; practice leaving the schedule alone).
`npm test` passes 16 of 16 and `npm run build` passes on Node.js 26.13.1. In
the browser, on a copy of the demo database with the browser in UTC+2, a
learned Barnes Opening line was saved due at 02:00 UTC the next day, the
lesson-complete screen showed "First review tomorrow from 04:00 AM", the
opening page's review button opened unhinted practice with the first-review
message, the repertoire showed "First test tomorrow" and the console had no
errors. The terminal demo reaches the review on the next day and passes with
`--grade Easy`; with its default `Good` (and with `Hard` or `Again`) it fails
on its grade check because its fixed response times predate the session
grading rule. That failure is unchanged from `66176b0` and is not fixed here.
It was fixed separately later on 2026-11-17 (see the [worklog](../worklog.md)).

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

1. Decided by the user on 2026-11-17: the next local day, starting at 04:00
   in the browser's time zone (UTC when the browser sends none).
2. Whether a failed same-day practice should do anything, such as offering
   the lesson again. The proposal keeps it off the schedule either way.
3. Whether same-day practice is logged as its own event type.
4. When the simulator and training follow, and whether the app change waits
   for retrained weights or ships first with the mismatch noted.

Closure: the app behavior is recorded in the App & Practice and System
Architecture records. This document stays open for the deferred simulator
and training follow-up and questions 2–4; once those are settled, its
remaining content moves to the owning records and it is retired with the
user's approval.
