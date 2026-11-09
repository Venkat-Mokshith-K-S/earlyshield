// Lives in shared/ (not the auth domain) because apiClient needs it, and
// shared code must not import from a domain.

const ACCESS_KEY = "es_access_token";
const REFRESH_KEY = "es_refresh_token";

export const tokenStorage = {
  // Fired whenever tokens are cleared (logout, or a refresh that failed),
  // so route guards can send the user back to /login.
  SIGNED_OUT_EVENT: "es:signed-out",

  getAccess: () => localStorage.getItem(ACCESS_KEY),
  getRefresh: () => localStorage.getItem(REFRESH_KEY),

  set(tokens: { access_token: string; refresh_token: string }) {
    localStorage.setItem(ACCESS_KEY, tokens.access_token);
    localStorage.setItem(REFRESH_KEY, tokens.refresh_token);
  },

  clear() {
    localStorage.removeItem(ACCESS_KEY);
    localStorage.removeItem(REFRESH_KEY);
    window.dispatchEvent(new Event(tokenStorage.SIGNED_OUT_EVENT));
  },
};
