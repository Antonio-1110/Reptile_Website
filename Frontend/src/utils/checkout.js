// Sends the payer to the payment provider when the API says a payment needs them there: either a page to
// open ({checkout_url}) or a signed form to post ({redirect_form: {action, fields}}, e.g. ECPay's hosted
// card page, which only accepts a form post). Returns true if the browser is on its way.
export function startCheckout(payment) {
  const form = payment?.redirect_form;
  if (form?.action) {
    const element = document.createElement("form");
    element.method = "POST";
    element.action = form.action;
    element.hidden = true;
    for (const [name, value] of Object.entries(form.fields || {})) {
      const input = document.createElement("input");
      input.type = "hidden";
      input.name = name;
      input.value = value;
      element.appendChild(input);
    }
    document.body.appendChild(element);
    element.submit();
    return true;
  }
  if (payment?.checkout_url) {
    window.location.assign(payment.checkout_url);
    return true;
  }
  return false;
}
