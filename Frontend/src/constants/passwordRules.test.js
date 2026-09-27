import { describe, expect, it } from "vitest";
import { passwordRuleStates } from "./passwordRules";

const met = (password) => Object.fromEntries(passwordRuleStates(password).map(({ key, met }) => [key, met]));

describe("passwordRuleStates", () => {
  it("ticks off length and letters as the password grows", () => {
    expect(met("")).toMatchObject({ minLength: false, notNumeric: false });
    expect(met("12345678")).toMatchObject({ minLength: true, notNumeric: false });
    expect(met("gecko")).toMatchObject({ minLength: false, notNumeric: true });
    expect(met("gecko-garden")).toMatchObject({ minLength: true, notNumeric: true });
  });

  it("leaves the rules only the server can check undecided", () => {
    expect(met("gecko-garden")).toMatchObject({ notSimilar: null, notCommon: null });
  });
});
