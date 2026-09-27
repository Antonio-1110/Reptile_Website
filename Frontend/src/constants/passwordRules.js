// Mirrors AUTH_PASSWORD_VALIDATORS in backend/backend/settings.py, which is what actually decides:
// this only lets the sign-up form list the rules and tick off the ones it can check as you type.
export const PASSWORD_MIN_LENGTH = 8;

// Each rule's `check` returns true/false when the browser can tell, or null when only the server can
// (similarity to your username or email, and Django's list of common passwords).
export const PASSWORD_RULES = [
  { key: "minLength", check: (password) => password.length >= PASSWORD_MIN_LENGTH },
  { key: "notNumeric", check: (password) => password.length > 0 && !/^\d+$/.test(password) },
  { key: "notSimilar", check: () => null },
  { key: "notCommon", check: () => null },
];

export function passwordRuleStates(password) {
  return PASSWORD_RULES.map(({ key, check }) => ({ key, met: check(password) }));
}
