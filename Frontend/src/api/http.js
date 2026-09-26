import i18n from "../i18n";

// UI language → the code the backend (Django LANGUAGES) expects in Accept-Language.
const API_LANGUAGE_CODES = { en: "en", zh: "zh-Hant" };

// VITE_API_URL points at the backend's /api root; every endpoint lives under its /v1/.
export const API_URL = `${import.meta.env.VITE_API_URL || "http://localhost:8000/api"}/v1`;

// fetch() for every API call: tells the backend the user's language (so its validation errors and
// messages come back translated) and turns network failures into a translated error.
export async function apiFetch(url, options = {}) {
  try {
    return await fetch(url, {
      ...options,
      headers: {
        "Accept-Language": API_LANGUAGE_CODES[i18n.resolvedLanguage] || "en",
        ...options.headers,
      },
    });
  } catch {
    throw new Error(i18n.t("errors.network"));
  }
}

// Fallback message when a response has no readable error body.
export function requestFailedMessage(status) {
  return i18n.t("errors.requestFailed", { status });
}
