import { appPref } from "./appPrefs.ts";
import { dueAt, isDue } from "./memory.ts";

/**
 * Review reminders in the Android app (mobile/README.md). The phone schedules them itself from the
 * repertoire's due times, so they arrive with the app closed and need no server.
 */
type ReminderLine = { line_id: number; opening_family: string; name: string; next_review_at: string; stability_days: number | null };
export type Reminder = { id: number; at: number; title: string; body: string };

export const FIRST_REMINDER_ID = 4100;
export const MAX_REMINDERS = 12;
const HOUR = 3_600_000;
export const QUIET_FROM_HOUR = 22;   // no reminders from 22:00 ...
export const QUIET_UNTIL_HOUR = 8;   // ... until 08:00
export const NUDGE_AFTER_MS = 3 * HOUR;   // openings already due: remind again later today
const HORIZON_MS = 14 * 24 * HOUR;

/** Move a time out of the quiet hours to 08:00 the next morning (or the same morning). */
export function outsideQuietHours(at: number): number {
  const date = new Date(at);
  const hour = date.getHours();
  if (hour >= QUIET_UNTIL_HOUR && hour < QUIET_FROM_HOUR) return at;
  const morning = new Date(date);
  if (hour >= QUIET_FROM_HOUR) morning.setDate(morning.getDate() + 1);
  morning.setHours(QUIET_UNTIL_HOUR, 0, 0, 0);
  return morning.getTime();
}

const openingName = (line: ReminderLine) => line.opening_family || line.name;

function message(lines: ReminderLine[]) {
  if (lines.length === 1) {
    return { title: `${openingName(lines[0])} is ready to review`, body: "Recall it now, before it fades." };
  }
  const names = [...new Set(lines.map(openingName))];
  const shown = names.slice(0, 2).join(", ") + (names.length > 2 ? ` and ${names.length - 2} more` : "");
  return { title: `${lines.length} openings are ready to review`, body: shown };
}

/**
 * When to remind: once for openings already due (a few hours from now), then once for each hour in
 * which more openings become due, outside quiet hours, for the next two weeks. Each reminder counts
 * every opening due by then.
 */
export function reminderPlan(lines: ReminderLine[], now: number): Reminder[] {
  const times = new Set<number>();
  if (lines.some((line) => isDue(line, now))) times.add(outsideQuietHours(now + NUDGE_AFTER_MS));
  for (const line of lines) {
    const due = dueAt(line);
    if (due > now && due - now <= HORIZON_MS) times.add(outsideQuietHours(Math.ceil(due / HOUR) * HOUR));
  }
  return [...times].sort((a, b) => a - b).slice(0, MAX_REMINDERS).map((at, index) => ({
    id: FIRST_REMINDER_ID + index,
    at,
    ...message(lines.filter((line) => dueAt(line) <= at)),
  }));
}

type Plugin = {
  checkPermissions(): Promise<{ display: string }>;
  requestPermissions(): Promise<{ display: string }>;
  getPending(): Promise<{ notifications: { id: number }[] }>;
  cancel(options: { notifications: { id: number }[] }): Promise<void>;
  schedule(options: { notifications: object[] }): Promise<unknown>;
  addListener(event: string, listener: (event: { notification: { extra?: { route?: string } } }) => void): Promise<unknown>;
};

/** The phone's notification plugin, or null on the website. */
export function notificationPlugin(): Plugin | null {
  const capacitor = (globalThis as { Capacitor?: { isNativePlatform?: () => boolean; Plugins?: Record<string, unknown> } }).Capacitor;
  if (!capacitor?.isNativePlatform?.()) return null;
  return (capacitor.Plugins?.LocalNotifications as Plugin | undefined) ?? null;
}

// Syncs run one after another: Android answers only one permission request at a time, and two
// overlapping syncs could cancel each other's reminders.
let queue: Promise<unknown> = Promise.resolve();

/** Replace TEMPO's scheduled reminders with a fresh plan; with reminders off, just remove them. */
export function syncReminders(lines: ReminderLine[], now = Date.now()): Promise<Reminder[]> {
  const run = queue.then(() => syncNow(lines, now));
  queue = run.catch(() => undefined);
  return run;
}

async function syncNow(lines: ReminderLine[], now: number): Promise<Reminder[]> {
  const plugin = notificationPlugin();
  if (!plugin) return [];
  try {
    const pending = (await plugin.getPending()).notifications.filter((item) =>
      item.id >= FIRST_REMINDER_ID && item.id < FIRST_REMINDER_ID + MAX_REMINDERS);
    if (pending.length) await plugin.cancel({ notifications: pending.map(({ id }) => ({ id })) });
    if (!appPref("reminders") || !lines.length) return [];
    let permission = (await plugin.checkPermissions()).display;
    if (permission.startsWith("prompt")) permission = (await plugin.requestPermissions()).display;
    if (permission !== "granted") return [];
    const plan = reminderPlan(lines, now);
    if (plan.length) {
      await plugin.schedule({
        notifications: plan.map((reminder) => ({
          id: reminder.id, title: reminder.title, body: reminder.body,
          schedule: { at: new Date(reminder.at), allowWhileIdle: true },
          extra: { route: "#/review" },
        })),
      });
    }
    return plan;
  } catch {
    return [];   // reminders are a convenience: never break the app over them
  }
}

/** Tapping a reminder opens Repeating. */
export function openRemindersOnTap() {
  void notificationPlugin()?.addListener("localNotificationActionPerformed", (event) => {
    window.location.hash = event.notification.extra?.route ?? "#/review";
  });
}
