import i18n from "../i18n";
import { API_URL, apiFetch, requestFailedMessage } from "./http";

const AUTH_URL = `${API_URL}/auth`;

const ACCESS_KEY = "accessToken";
const REFRESH_KEY = "refreshToken";

function readStorage(key) {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}

function writeTokens({ access, refresh }) {
  try {
    if (access) localStorage.setItem(ACCESS_KEY, access);
    if (refresh) localStorage.setItem(REFRESH_KEY, refresh);
  } catch {
    // Storage unavailable (private mode etc.); the user just won't stay signed in.
  }
}

export function clearTokens() {
  try {
    localStorage.removeItem(ACCESS_KEY);
    localStorage.removeItem(REFRESH_KEY);
  } catch {
    // Nothing to clear.
  }
}

export function getAccessToken() {
  return readStorage(ACCESS_KEY);
}

export function isLoggedIn() {
  return Boolean(getAccessToken());
}

// Turns an API error body into {message, fields}. The backend always answers errors with
// {detail: "message"} for the request as a whole and/or {field: ["message", …]} (common/exceptions.py);
// SimpleJWT adds `code` and `messages`, which aren't fields.
async function parseError(response) {
  const body = await response.json().catch(() => ({}));
  const fields = {};
  Object.entries(body).forEach(([key, value]) => {
    if (key !== "detail" && key !== "code" && key !== "messages") {
      fields[key] = Array.isArray(value) ? value.join(" ") : String(value);
    }
  });
  const message = typeof body.detail === "string" && body.detail
    ? body.detail
    : Object.values(fields).join(" ") || requestFailedMessage(response.status);
  const error = new Error(message);
  error.status = response.status;
  error.fields = fields;
  return error;
}

async function postJson(path, payload) {
  const response = await apiFetch(`${AUTH_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) throw await parseError(response);
  return response.json();
}

// Shared so several requests failing with 401 at once trigger a single refresh.
let refreshPromise = null;

async function refreshAccessToken() {
  const refresh = readStorage(REFRESH_KEY);
  if (!refresh) return false;
  refreshPromise ??= postJson("/refresh/", { refresh })
    .then((tokens) => {
      writeTokens(tokens);
      return true;
    })
    .catch(() => {
      // Each refresh token works once. If another tab used it first, that tab has already stored
      // the new pair, which this tab can use; only a token nobody replaced means the session is over.
      if (readStorage(REFRESH_KEY) !== refresh) return true;
      clearTokens();
      return false;
    })
    .finally(() => {
      refreshPromise = null;
    });
  return refreshPromise;
}

// fetch() against the API with the JWT attached; retries once after refreshing an expired token.
export async function authFetch(path, options = {}) {
  const send = () => {
    const token = getAccessToken();
    return apiFetch(`${API_URL}${path}`, {
      ...options,
      headers: {
        // FormData bodies (photo uploads) need the browser to set the multipart boundary itself.
        ...(options.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...options.headers,
      },
    });
  };

  const hadToken = Boolean(getAccessToken());
  let response = await send();
  if (response.status === 401 && hadToken && await refreshAccessToken()) {
    response = await send();
  }
  if (!response.ok) {
    const error = await parseError(response);
    // DRF's own 401 text ("Given token not valid for any token type") means nothing to users.
    if (response.status === 401) {
      error.message = i18n.t(hadToken ? "errors.sessionExpired" : "errors.signInRequired");
    }
    throw error;
  }
  if (response.status === 204) return null;
  return response.json();
}

export async function login(username, password) {
  writeTokens(await postJson("/login/", { username, password }));
}

// `credential` is the ID token from Google's sign-in button; the answer is the same token pair as login.
// Resolves to whether this sign-in created a new account.
export async function googleSignIn(credential) {
  const tokens = await postJson("/google/", { credential });
  writeTokens(tokens);
  return Boolean(tokens.created);
}

export async function register({ username, email, password }) {
  await postJson("/register/", { username, email, password });
  try {
    await login(username, password);
  } catch (error) {
    error.accountCreated = true;
    throw error;
  }
}

// Forgets the tokens here and retires the refresh token on the server, so a copy of it can't be used
// to stay signed in. Signing out still succeeds locally if that request fails.
export async function logout() {
  const refresh = readStorage(REFRESH_KEY);
  clearTokens();
  if (!refresh) return;
  await postJson("/logout/", { refresh }).catch(() => {});
}

export async function getMe() {
  return authFetch("/auth/me/", { method: "GET" });
}

// The links in sign-up and password-reset emails carry a uid and token that go straight back to the API.
export async function verifyEmail({ uid, token }) {
  return postJson("/verify-email/", { uid, token });
}

export async function resendVerificationEmail() {
  return authFetch("/auth/verify-email/resend/", { method: "POST" });
}

export async function requestPasswordReset(email) {
  return postJson("/password-reset/", { email });
}

export async function resetPassword({ uid, token, password }) {
  return postJson("/password-reset/confirm/", { uid, token, password });
}

// Answers with a new token pair: the server signs every other device out, this one included, so the
// pair is what keeps this device signed in.
export async function changePassword({ currentPassword, password }) {
  const response = await authFetch("/auth/password-change/", {
    method: "POST",
    body: JSON.stringify({ current_password: currentPassword, password }),
  });
  writeTokens(response);
  return response.detail;
}
