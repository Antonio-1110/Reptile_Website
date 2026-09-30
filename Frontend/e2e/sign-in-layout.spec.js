import { expect, test } from '@playwright/test';

// The sign-in form has to be usable without scrolling on a laptop (a MacBook Air's browser window is
// about 1280×680 or 1440×780 of page), and stay one column on a phone. Unit tests have no layout
// engine, so the geometry is checked here, in both languages.

// Google's script is replaced by a stand-in button the size of the real one, so the test doesn't
// depend on reaching Google.
const GOOGLE_STUB = `window.google = { accounts: { id: { initialize() {}, renderButton(el, options) {
  const button = document.createElement('div');
  button.className = 'fakeGoogleButton';
  button.style.cssText = 'height:44px;width:' + options.width + 'px';
  el.appendChild(button);
} } } };`;

async function openSignIn(page, language, { width, height }, path) {
  await page.route('https://accounts.google.com/gsi/client', (route) => route.fulfill({ contentType: 'text/javascript', body: GOOGLE_STUB }));
  await page.addInitScript((lng) => localStorage.setItem('i18nextLng', lng), language);
  await page.setViewportSize({ width, height });
  await page.goto(path);
  await expect(page.locator('.fakeGoogleButton')).toBeVisible();
}

async function measure(page) {
  return page.evaluate(() => {
    const box = (selector) => {
      const rect = document.querySelector(selector).getBoundingClientRect();
      return { left: rect.left, right: rect.right, top: rect.top, bottom: rect.bottom };
    };
    return {
      intro: box('.authIntro'),
      form: box('.authForm'),
      submit: box('.authSubmit'),
      google: box('.fakeGoogleButton'),
      pageWidth: document.documentElement.scrollWidth,
      viewportWidth: window.innerWidth,
      viewportHeight: window.innerHeight,
    };
  });
}

for (const language of ['en', 'zh']) {
  test.describe(`sign-in layout (${language})`, () => {
    test('on a laptop the whole form, Google included, fits without scrolling', async ({ page }) => {
      for (const viewport of [{ width: 1280, height: 680 }, { width: 1440, height: 780 }]) {
        // /settings needs an account, so it sends the visitor here with the "we'll take you back" notice:
        // the tallest version of the sign-in form.
        for (const path of ['/settings', '/signin?mode=register']) {
          await openSignIn(page, language, viewport, path);
          const m = await measure(page);
          const where = `${path} at ${viewport.width}×${viewport.height}`;
          expect(m.pageWidth, `the page scrolls sideways (${where})`).toBeLessThanOrEqual(m.viewportWidth);
          expect(m.submit.bottom, `the submit button is below the fold (${where})`).toBeLessThanOrEqual(m.viewportHeight);
          expect(m.google.bottom, `Google is below the fold (${where})`).toBeLessThanOrEqual(m.viewportHeight);
          expect(m.form.left, `the form isn't beside the intro (${where})`).toBeGreaterThan(m.intro.right);
        }
      }
    });

    test('on a phone it stays one column, with Google under the form', async ({ page }) => {
      await openSignIn(page, language, { width: 375, height: 700 }, '/signin');
      const m = await measure(page);
      expect(m.pageWidth, 'the page scrolls sideways').toBeLessThanOrEqual(m.viewportWidth);
      expect(m.form.top).toBeGreaterThanOrEqual(m.intro.bottom);
      expect(m.google.top).toBeGreaterThan(m.submit.bottom);
    });
  });
}

test('the "take you back" notice shows only to visitors who were sent to sign in', async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem('i18nextLng', 'en'));
  await page.goto('/marketplace');
  await page.locator('.header').getByRole('link', { name: 'Sign in' }).click();
  await expect(page).toHaveURL(/\/signin\?next=/);
  await expect(page.getByRole('heading', { name: 'Welcome back' })).toBeVisible();
  await expect(page.locator('.authNotice')).toHaveCount(0);

  await page.goto('/settings');
  await expect(page.locator('.authNotice')).toContainText("we'll take you back");
});
