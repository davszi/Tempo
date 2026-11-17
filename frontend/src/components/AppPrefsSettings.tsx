import { useState } from "react";
import { Bell, Volume2 } from "lucide-react";
import { appPref, setAppPref, type AppPref } from "../lib/appPrefs";
import { playSound } from "../lib/sound";

/** Settings that only exist in the Android app: sounds and review reminders. */
export function AppPrefsSettings() {
  const [prefs, setPrefs] = useState(() => ({ sounds: appPref("sounds"), reminders: appPref("reminders") }));
  function change(name: AppPref, on: boolean) {
    setAppPref(name, on);
    setPrefs((current) => ({ ...current, [name]: on }));
    if (name === "sounds" && on) playSound("savedGood");
  }
  return <section className="card app-prefs" aria-label="Phone app">
    <label className="app-pref">
      <span><b><Volume2 size={16} /> Sounds</b><small>A click for each move, a buzz for a mistake, a chime when a review is saved.</small></span>
      <input type="checkbox" checked={prefs.sounds} onChange={(event) => change("sounds", event.target.checked)} />
    </label>
    <label className="app-pref">
      <span><b><Bell size={16} /> Review reminders</b><small>A notification when openings become due, never between 22:00 and 08:00.</small></span>
      <input type="checkbox" checked={prefs.reminders} onChange={(event) => change("reminders", event.target.checked)} />
    </label>
  </section>;
}
