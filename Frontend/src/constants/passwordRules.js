// Mirrors AUTH_PASSWORD_VALIDATORS in backend/backend/settings.py, which is what actually decides:
// this only lets the sign-up and reset forms list the rules and tick them off as you type.
export const PASSWORD_MIN_LENGTH = 8;

export const PASSWORD_RULES = [
  { key: "minLength", check: (password) => password.length >= PASSWORD_MIN_LENGTH },
  { key: "lettersAndNumbers", check: (password) => /[A-Za-z]/.test(password) && /\d/.test(password) },
];

export function passwordRuleStates(password) {
  return PASSWORD_RULES.map(({ key, check }) => ({ key, met: check(password) }));
}
