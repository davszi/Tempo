# Open work

Routes only. The linked owner holds the checklist, rationale and evidence.

- Starter adoption: [guide acceptance checklist](../topics/guide/guide.md#acceptance-checklist) owns configuration replacement, kit initialization and integration review.
- Opening catalog restructure (family sides, merged gambits, line tree, learnable subvariations) awaits team confirmation and implementation: [opening catalog structure](../topics/opening-catalog/opening-catalog.md#open-questions).
- Side labels of the opening library await team confirmation: [opening library open questions](../topics/opening-library/opening-library.md#open-questions).
- Recall per line, extra dataset columns and ML engine start-up proposals await team decisions: [FSRS training open questions](../topics/fsrs-training/fsrs-training.md#open-questions).
- Retraining both FSRS-6 variants on the cleaned catalog, with true-recall arms, a days metric and dataset removal: [retraining plan](../topics/fsrs-training/retraining-plan.md).
- [Product to-dos](#product-to-dos) covers forgetting estimates, benchmark metrics, review intervals, the schedule view, repertoire access, and cleaning the opening dataset.

## Product to-dos

### 1. Show "days until you forget" for each opening line

**Goal:** the player can see, per learned line, roughly how many days they have before they are likely to forget it.

**Details:**
- Derive the value from the FSRS state already stored in `player_lines.fsrs_state`. `MLEngine.stability_days` in `backend/ml_engine.py` already returns the card's stability in days.
- Define "forget" precisely before building it. Two candidate definitions:
  - days until the scheduled review, `next_review_at - now` (the moment retrievability falls to the scheduler's desired retention, 90% by default);
  - days until retrievability drops below a lower threshold, such as 50%, computed from the FSRS forgetting curve.
- Pick one, document it, and show it with its meaning (for example "≈ 12 days until recall drops below 90%").
- Handle the edge cases: lines that are only learned and never reviewed (stability is `None`), lines that are already overdue (show "overdue by N days" rather than a negative number), and lines due today.
- Add an engine method that returns this value so the UI and the demo use the same calculation, and print it in `backend/demo.py` next to the stability.

**Done when:** each learned line shows a days-until-forgetting value that matches the FSRS state, and the edge cases above are covered by tests.

### 2. Give context to the benchmark improvements (loss functions)

**Goal:** anyone reading the benchmark results can tell what each loss number measures and why a lower value is better.

**Details:**
- For each reported metric, write a short plain-language explanation next to the result. Expected metrics for FSRS-style evaluation:
  - **Log loss:** how well the predicted recall probability matches whether the player actually recalled the line; it penalizes confident wrong predictions heavily.
  - **RMSE (binned):** the average gap between predicted and observed recall rates across probability bins, which shows calibration.
  - Any other metric used (such as AUC) with the same kind of explanation.
- State what is being compared: TEMPO's per-player fitted parameters against a baseline, such as default FSRS-6 weights or a fixed-interval rule like the ones most trainers use (see `docs/PROJECT_CONTEXT.md`).
- Record the setup next to the numbers: which synthetic personas (`docs/topics/synthetic-clients/`), how many simulated reviews, the train/test split, the parameter files used, and the command to reproduce the run.
- Explain how big a difference has to be to matter. Include the spread across personas or random seeds, not only one averaged number.
- No benchmark code or results are in the repository yet. This item includes adding the run and its record.
- Include the ground truth loss function.

**Done when:** the benchmark record lists every metric with an explanation, the baseline, the setup and a reproduction command, and a reader can tell from it whether TEMPO improved and by how much.

### 3. Make the improvements concrete in terms of days

**Goal:** turn abstract loss improvements into statements a chess player understands, for example "our algorithm consistently schedules longer intervals for lines you know well, without more forgetting".

**Details:**
- For the same simulated players, compare TEMPO with the baseline on outcomes measured in days and reviews:
  - average interval between reviews (days) for well-known lines and for weak lines separately;
  - number of reviews needed to keep a repertoire at the target recall rate over a fixed period (for example 90 days);
  - share of reviews where the player forgot the line (graded `Again`);
  - how often the interval is too long (the line was forgotten) or too short (the review came while the line was still well remembered).
- Check the claim "consistently predicts bigger day amounts" on every persona, not only on average. If it holds for some personas and not others, say which and why. Longer intervals are only an improvement if forgetting does not increase.
- Present one or two worked examples, for example: "Persona *Steady*, line X: baseline reviews every 4 days, TEMPO every 9 days, same recall rate".
- Show the comparison as a simple chart or table per persona.

**Done when:** the results state, with numbers per persona, how many days and reviews TEMPO saves or costs compared with the baseline, and what happens to the forgetting rate.

### 4. Add a visual view of the review schedule

**Goal:** the player can see at a glance which lines are due and when the upcoming reviews fall.

**Details:**
- Build the view from `player_lines.next_review_at` (indexed by `player_id, next_review_at` in `backend/store.py`).
- Suggested layout: a timeline or calendar for the next 30 days with the number of lines due per day, with today and overdue lines highlighted.
- Selecting a day lists the lines due that day, with their days-until-forgetting value from item 1.
- Optionally show each line's history: past review dates, grades (`Again`, `Hard`, `Good`, `Easy`) and how the interval grew, from `practice_events`.
- Make sure the view uses the same "now" and time zone as `practice_controller.py` (UTC stored, local time shown).

**Done when:** the schedule view shows due and upcoming reviews that match the database, including overdue lines, and works with an empty repertoire.

### 5. Make the repertoire easy to reach in the UI

**Goal:** the player can open their repertoire from anywhere in the app without starting a practice session.

**Details:**
- Add a permanent entry (navigation tab or button) for the repertoire.
- List every line the player has learned: opening family, name, ECO code, side (white, black or both), and the moves (`opening_lines` and `player_lines`).
- Show the practice status per line: date learned, last review and grade, next review date, and days until forgetting (item 1).
- Allow search or filtering by opening family, side and status (due, upcoming, not yet learned).
- From a line, let the player start Learning or Repeating directly through the existing `PracticeController` calls (`start_learning`, `start_repeating`).
- Lines available but not yet learned (`list_lines`) should be shown separately so the player can add them.

**Done when:** the repertoire opens from any screen, lists all learned and available lines with their status, and practice can be started from it.

### 6. Clean the opening dataset

**Goal:** the opening library holds only lines long enough to be worth training, with every line of 3 moves or less removed.

**Details:**
- Source: `ml/ml_1000bots/openings/lichess_openings.tsv` (3,865 lines) and the derived `lichess_openings_classified.csv`, which `ml/ml_1000bots/openings/classify.py` writes.
- "3 moves or less" means 3 full moves or fewer (the `white_moves` column is 3 or less), which removes 1,146 lines. Counted in half-moves (`plies` column is 3 or less) it would remove only 269. Confirm the definition before deleting.
- Filter in `classify.py` (or a separate cleaning step) rather than editing the TSV by hand, so the library can be rebuilt from the Lichess source. Record the rule and the new line count and sha256 in the [opening library record](../topics/opening-library/opening-library.md).
- The simulator already draws only lines with 4 to 16 player moves (`user_moves` in `ml/ml_1000bots/tempo_sim/config.py`), so dataset `tempo_v1` contains no short lines and does not need regenerating.
- Check that `frontend/src/data/openings.ts` and the demo database contain no short lines either.

**Done when:** no line of 3 moves or less remains in the library files, the filter is reproducible from the script, and the opening library record states the rule and the new counts.

**Note:** the React frontend in `frontend/` supports Learning and Repeating. Items 4 and 5 cover the schedule and repertoire views.
