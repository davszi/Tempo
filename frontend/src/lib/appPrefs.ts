/** On/off settings that only exist in the Android app (mobile/README.md). Both default to on. */
const KEYS = { sounds: "tempo-sounds", reminders: "tempo-reminders" } as const;
export type AppPref = keyof typeof KEYS;
export const APP_PREFS_EVENT = "tempo-app-prefs";

export function appPref(name: AppPref): boolean {
  try { return localStorage.getItem(KEYS[name]) !== "off"; } catch { return true; }
}

export function setAppPref(name: AppPref, on: boolean) {
  try { localStorage.setItem(KEYS[name], on ? "on" : "off"); } catch { /* storage unavailable: keep the default */ }
  window.dispatchEvent(new Event(APP_PREFS_EVENT));
}
