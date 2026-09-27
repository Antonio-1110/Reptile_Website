import { describe, expect, it } from "vitest";
import { passwordRuleStates } from "./passwordRules";

const met = (password) => Object.fromEntries(passwordRuleStates(password).map(({ key, met }) => [key, met]));

describe("passwordRuleStates", () => {
  it("needs 8 characters with both English letters and numbers", () => {
    expect(met("")).toEqual({ minLength: false, lettersAndNumbers: false });
    expect(met("12345678")).toEqual({ minLength: true, lettersAndNumbers: false });
    expect(met("onlyletters")).toEqual({ minLength: true, lettersAndNumbers: false });
    expect(met("gecko1")).toEqual({ minLength: false, lettersAndNumbers: true });
    expect(met("gecko123")).toEqual({ minLength: true, lettersAndNumbers: true });
  });
});
