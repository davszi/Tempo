import test from "node:test";
import assert from "node:assert/strict";
import { FIRST_REMINDER_ID, MAX_REMINDERS, NUDGE_AFTER_MS, outsideQuietHours, reminderPlan } from "../src/lib/reminders.ts";

const HOUR = 3_600_000;
const at = (hour, minute = 0, day = 18) => new Date(2026, 10, day, hour, minute).getTime();   // local time, 18 Nov 2026
const line = (line_id, family, dueTime, name = family) =>
  ({ line_id, opening_family: family, name, next_review_at: new Date(dueTime).toISOString(), stability_days: 3 });

test("reminders never fall between 22:00 and 08:00", () => {
  assert.equal(outsideQuietHours(at(14)), at(14));
  assert.equal(outsideQuietHours(at(23, 30)), at(8, 0, 19));
  assert.equal(outsideQuietHours(at(3)), at(8));
  assert.equal(outsideQuietHours(at(8)), at(8));
  assert.equal(outsideQuietHours(at(21, 59)), at(21, 59));
});

test("an opening becoming due later today is announced at the start of that hour, by name", () => {
  const plan = reminderPlan([line(1, "London System", at(15, 20))], at(10));
  assert.equal(plan.length, 1);
  assert.equal(plan[0].at, at(16));
  assert.equal(plan[0].id, FIRST_REMINDER_ID);
  assert.equal(plan[0].title, "London System is ready to review");
});

test("openings already due get one nudge a few hours later that counts them all", () => {
  const now = at(12);
  const plan = reminderPlan([line(1, "London System", at(9)), line(2, "Italian Game", at(11)), line(3, "Caro-Kann Defense", at(10))], now);
  assert.equal(plan.length, 1);
  assert.equal(plan[0].at, now + NUDGE_AFTER_MS);
  assert.equal(plan[0].title, "3 openings are ready to review");
  assert.equal(plan[0].body, "London System, Italian Game and 1 more");
});

test("openings due in the same hour share one reminder, and later ones count the earlier", () => {
  const plan = reminderPlan([
    line(1, "London System", at(15, 5)), line(2, "Italian Game", at(15, 40)), line(3, "Scotch Game", at(17, 10)),
  ], at(10));
  assert.deepEqual(plan.map((item) => item.at), [at(16), at(18)]);
  assert.equal(plan[0].title, "2 openings are ready to review");
  assert.equal(plan[1].title, "3 openings are ready to review");
});

test("a night-time due date is announced at 08:00", () => {
  const plan = reminderPlan([line(1, "Vienna Game", at(2, 30, 19))], at(20));
  assert.deepEqual(plan.map((item) => item.at), [at(8, 0, 19)]);
});

test("the plan is limited and skips openings due more than two weeks ahead", () => {
  const lines = Array.from({ length: 30 }, (_, index) => line(index, `Opening ${index}`, at(9) + (index + 1) * 2 * HOUR));
  const plan = reminderPlan(lines, at(9));
  assert.equal(plan.length, MAX_REMINDERS);
  assert.deepEqual(plan.map((item) => item.id), plan.map((_, index) => FIRST_REMINDER_ID + index));
  assert.equal(reminderPlan([line(1, "French Defense", at(9) + 20 * 24 * HOUR)], at(9)).length, 0);
});

test("with nothing learned there is nothing to remind", () => {
  assert.deepEqual(reminderPlan([], at(9)), []);
});
