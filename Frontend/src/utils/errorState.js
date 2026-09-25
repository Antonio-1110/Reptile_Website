// Error state for async loads: keeps the server's (already translated) message, or a translation
// key to resolve at render time. Storing the key rather than translated text keeps effects free of
// `t` and lets the message follow a language switch.
export function toErrorState(error, fallbackKey) {
  return error?.message ? { message: error.message } : { key: fallbackKey };
}

export function errorText(t, state) {
  return state ? state.message || t(state.key) : "";
}
