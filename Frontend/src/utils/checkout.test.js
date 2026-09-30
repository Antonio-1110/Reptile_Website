import { afterEach, describe, expect, it, vi } from "vitest";
import { startCheckout } from "./checkout";

describe("startCheckout", () => {
  afterEach(() => {
    document.body.innerHTML = "";
    vi.restoreAllMocks();
  });

  it("posts a provider's signed form with every field", () => {
    const submit = vi.spyOn(HTMLFormElement.prototype, "submit").mockImplementation(() => {});
    const started = startCheckout({
      redirect_form: { action: "https://payment-stage.ecpay.com.tw/Cashier/AioCheckOut/V5", fields: { MerchantID: "3002607", TotalAmount: "500" } },
    });
    expect(started).toBe(true);
    const form = document.querySelector("form");
    expect(form.method).toBe("post");
    expect(form.action).toBe("https://payment-stage.ecpay.com.tw/Cashier/AioCheckOut/V5");
    expect(Object.fromEntries(new FormData(form))).toEqual({ MerchantID: "3002607", TotalAmount: "500" });
    expect(submit).toHaveBeenCalledOnce();
  });

  it("does nothing when the payment needs no checkout", () => {
    expect(startCheckout({})).toBe(false);
    expect(startCheckout(undefined)).toBe(false);
    expect(document.querySelector("form")).toBeNull();
  });
});
