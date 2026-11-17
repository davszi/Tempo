import test from "node:test";
import assert from "node:assert/strict";
import { isMobileApp, markMobileApp } from "../src/lib/platform.ts";

const ANDROID_WEBVIEW = "Mozilla/5.0 (Linux; Android 15; DN2101 Build/AP3A; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/131.0 Mobile Safari/537.36";
const DESKTOP_CHROME = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36";

test("the Android app is recognised by the tag it appends to its user agent", () => {
  assert.equal(isMobileApp(`${ANDROID_WEBVIEW} TEMPO-App`), true);
});

test("browsers, including phone browsers, are not the app", () => {
  assert.equal(isMobileApp(DESKTOP_CHROME), false);
  assert.equal(isMobileApp(ANDROID_WEBVIEW), false);
  assert.equal(isMobileApp(`${ANDROID_WEBVIEW} TEMPO-Appx`), false);
  assert.equal(isMobileApp(""), false);
});

test("markMobileApp sets the mobile-app class only inside the app", () => {
  const classes = new Set();
  const root = { classList: { toggle: (name, on) => (on ? classes.add(name) : classes.delete(name)) } };
  Object.defineProperty(globalThis, "navigator", { value: { userAgent: `${ANDROID_WEBVIEW} TEMPO-App` }, configurable: true });
  markMobileApp(root);
  assert.deepEqual([...classes], ["mobile-app"]);
  Object.defineProperty(globalThis, "navigator", { value: { userAgent: DESKTOP_CHROME }, configurable: true });
  markMobileApp(root);
  assert.deepEqual([...classes], []);
});
