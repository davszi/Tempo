/**
 * The TEMPO Android app opens the live site and adds "TEMPO-App" to its user agent
 * (mobile/README.md). Use this to make a change apply only inside the app:
 *
 *   if (isMobileApp()) { ... }
 *
 * For styles, `markMobileApp()` adds the `mobile-app` class to <html>, so CSS can use
 * `.mobile-app .some-class { ... }` without changing the website.
 */
export const MOBILE_APP_TAG = "TEMPO-App";

export function isMobileApp(userAgent: string = globalThis.navigator?.userAgent ?? ""): boolean {
  return userAgent.split(/\s+/).includes(MOBILE_APP_TAG);
}

export function markMobileApp(root: { classList: { toggle(name: string, on: boolean): void } } | undefined = globalThis.document?.documentElement) {
  root?.classList.toggle("mobile-app", isMobileApp());
}
