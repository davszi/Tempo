# TEMPO on Android

The Android app has no copy of TEMPO inside it. It is a window onto a website:

| App | Opens | Use |
|---|---|---|
| **TEMPO** (`com.tempo.chessdemo`) | the live site, https://tempo-5nf3.onrender.com, built from `main` | everyone; updates itself whenever `main` deploys |
| **TEMPO Dev** (`com.tempo.chessdemo.dev`) | `http://localhost:5173` on your PC, over USB | testing a branch on a phone before it reaches `main` |

Both apps add `TEMPO-App` to their browser user agent, so the site can tell it is inside the app.

## Making a change only for the app

Anything merged to `main` reaches the website and the app together. To change only the app:

```ts
import { isMobileApp } from "./lib/platform";

if (isMobileApp()) {
  // app-only behaviour
}
```

For styles, the `<html>` element has the class `mobile-app` inside the app only:

```css
.mobile-app .bottom-nav { padding-bottom: 12px; }
```

Outside the app `isMobileApp()` is `false` and no `.mobile-app` rule matches, so the website stays exactly as it is.
`frontend/tests/platform.test.mjs` checks that browsers, including phone browsers, are never treated as the app.

## What the app adds to the website

Everything below runs only inside the app (`isMobileApp()`); the website is unchanged.

- **Repeating as a feed.** Each review is a full-screen card. Swipe up anywhere on it for the next
  due opening, which rises from below. Before the line is finished this skips it without a grade:
  it stays due and comes back after the others (`lib/reviewQueue.ts`). A drag that starts on one of
  your pieces is always a move. Swipe down to look back at the cards left behind, read-only; a
  skipped one can be reviewed from there.
- **Sounds** for moves, mistakes and saved reviews, made with the Web Audio API (`lib/sound.ts`).
- **Review reminders** scheduled on the phone from the repertoire's due times, never between 22:00
  and 08:00 (`lib/reminders.ts`). They use the `@capacitor/local-notifications` plugin built into
  the APK, so they need no server. Tapping one opens Repeating.
- Settings has a "Phone app" section to turn sounds and reminders off.

## Testing a branch on the phone

1. Install **TEMPO Dev** once (`TEMPO-Dev.apk`), next to the normal TEMPO app.
2. Plug the phone in by USB with USB debugging allowed.
3. From the repository root, on your branch, run:

   ```powershell
   .\mobile\dev-phone.ps1
   ```

   It starts the backend (port 8000), builds the frontend and serves it on port 5173, each in its own window,
   forwards the phone's `localhost:5173` to the PC, and opens TEMPO Dev.
   Testing uses a copy of the demo database in `%TEMP%`, so `backend/tempo_demo.sqlite` is never changed.
4. Edit files in `frontend/src`. The "TEMPO rebuild on save" window rebuilds after each save;
   when it says `built in`, run the script again to reopen the app with your change.

`-HotReload` uses the Vite dev server instead, so the phone updates by itself. It sends dozens of files
at once, which can jam the USB connection and leave a blank screen; running the script again resets it.
If the phone stops answering altogether, run `adb kill-server` and the script again.

## When a new APK is needed

Only for changes to the app shell itself: its name, icon, version, the site it opens, or a new native plugin.
Website changes, including app-only ones, never need a new APK. Both apps include
`@capacitor/local-notifications` 8.3.1 and a status-bar icon `res/drawable/ic_stat_tempo.xml`.

The two Android projects are outside the repository, in `%USERPROFILE%\AndroidDev\tempo-app` (TEMPO) and
`...\tempo-app-dev` (TEMPO Dev), with the JDK and Android SDK used to build them. To rebuild one:

```powershell
$env:JAVA_HOME = "$env:USERPROFILE\AndroidDev\jdk-21.0.13+9"; $env:ANDROID_HOME = "$env:USERPROFILE\AndroidDev\sdk"
cd $env:USERPROFILE\AndroidDev\tempo-app; npx cap sync android; cd android; .\gradlew.bat assembleDebug
```

Raise `versionCode` in `android/app/build.gradle` first, so the new APK installs over the old one.
The APK is written to `android/app/build/outputs/apk/debug/app-debug.apk`.
