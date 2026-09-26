import i18n from "../i18n";
import { apiFetch, requestFailedMessage } from "./http";

const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000/api";
const AUTH_URL = `${API_BASE_URL}/v1/auth`;

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

// Turns a DRF error body ({detail}, {field: [msgs]}) into {message, fields}.
async function parseError(response) {
  const body = await response.json().catch(() => ({}));
  const fields = {};
  Object.entries(body).forEach(([key, value]) => {
    if (key !== "detail" && key !== "code" && key !== "messages") {
      fields[key] = Array.isArray(value) ? value.join(" ") : String(value);
    }
  });
  // `detail` is usually a string, but serializer-level errors raised as {'detail': ...} arrive as a list.
  const detail = Array.isArray(body.detail) ? body.detail.join(" ") : body.detail;
  const message = typeof detail === "string" && detail
    ? detail
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
    return apiFetch(`${API_BASE_URL}${path}`, {
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

export async function register({ username, email, password }) {
  await postJson("/register/", { username, email, password });
  try {
    await login(username, password);
  } catch (error) {
    error.accountCreated = true;
    throw error;
  }
}

export function logout() {
  clearTokens();
}

export async function getMe() {
  return authFetch("/v1/auth/me/", { method: "GET" });
}
