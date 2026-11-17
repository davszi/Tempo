/** Player accounts. The backend keeps the session in an HttpOnly cookie; this module only calls it. */
export type Account = { user_id: string; name: string; email: string | null; has_password: boolean; google: boolean };
export type AuthState = { user: Account | null; google_client_id: string | null };

const PLAYER_KEY = "tempo-player";

async function authRequest<T>(path: string, body?: object): Promise<T> {
  const response = await fetch(`/api/auth/${path}`, body === undefined ? { credentials: "same-origin" } : {
    method: "POST", credentials: "same-origin",
    headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
  });
  if (!response.headers.get("content-type")?.includes("application/json")) {
    throw new Error("Cannot reach TEMPO. Start the Python backend and try again.");
  }
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || "The request failed.");
  return result;
}

export const fetchAuthState = () => authRequest<AuthState>("me");
export const register = (name: string, email: string, password: string) =>
  authRequest<{ user: Account }>("register", { name, email, password });
export const login = (email: string, password: string) => authRequest<{ user: Account }>("login", { email, password });
export const requestPasswordReset = (email: string) => authRequest<{ ok: boolean }>("forgot-password", { email });
export const resetPassword = (token: string, password: string) => authRequest<{ ok: boolean }>("reset-password", { token, password });
export const googleSignIn = (credential: string) =>
  authRequest<{ user: Account }>("google", { credential });
export const logout = () => authRequest<{ user: null }>("logout", {});
export const updateProfile = (name: string, email: string) => authRequest<{ user: Account }>("profile", { name, email });
export const changePassword = (currentPassword: string, newPassword: string) =>
  authRequest<{ user: Account }>("password", { current_password: currentPassword, new_password: newPassword });
export const deleteAccount = (password: string, confirm: string) => authRequest<{ user: null }>("delete", { password, confirm });

const GUEST_KEY = "tempo-guest-player";

/**
 * Practice requests carry the account's ID while signed in. A new account starts empty, so the guest's own
 * ID is kept aside on sign-in and given back on sign-out: the guest's progress on this device is never lost.
 */
export function rememberAccount(user: Account | null) {
  try {
    if (user) {
      const current = localStorage.getItem(PLAYER_KEY);
      if (current && current !== user.user_id && !localStorage.getItem(GUEST_KEY)) localStorage.setItem(GUEST_KEY, current);
      localStorage.setItem(PLAYER_KEY, user.user_id);
    } else {
      const guest = localStorage.getItem(GUEST_KEY);
      if (guest) localStorage.setItem(PLAYER_KEY, guest);
      else localStorage.removeItem(PLAYER_KEY);
    }
  } catch { /* storage unavailable: the backend still uses the session cookie */ }
}
