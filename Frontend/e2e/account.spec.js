import { expect, test } from '@playwright/test';
import { API, expectNoConsoleErrors, signIn, submitSignIn, useEnglish } from './helpers';

test('signing out from the account menu ends the session', async ({ page }) => {
  const errors = [];
  page.on('console', (message) => message.type() === 'error' && errors.push(message.text()));
  await useEnglish(page);
  await signIn(page, 'buyer_hsu', '/marketplace');

  await page.getByRole('button', { name: 'My account' }).click();
  await page.getByRole('button', { name: 'Sign out' }).click();

  await expect(page.getByRole('link', { name: 'Sign In' })).toBeVisible();
  expect(await page.evaluate(() => localStorage.getItem('accessToken'))).toBeNull();
  // A signed-in-only page now asks to sign in instead of showing the old account's data.
  await page.goto('/settings');
  await expect(page).toHaveURL(/\/signin/);
  await expectNoConsoleErrors(errors);
});

test('changing the password from settings signs other devices out', async ({ page, request }) => {
  const errors = [];
  page.on('console', (message) => message.type() === 'error' && errors.push(message.text()));
  await useEnglish(page);
  // A new account, so changing its password can't affect the demo accounts other tests sign in to.
  const username = `pw_${Date.now()}`;
  await request.post(`${API}/auth/register/`, { data: { username, email: `${username}@example.com`, password: 'OldPass123' } });
  const otherDevice = await (await request.post(`${API}/auth/login/`, { data: { username, password: 'OldPass123' } })).json();
  await page.goto('/signin?next=%2Fsettings');
  await page.getByLabel('Username or email').fill(username);
  await page.getByLabel('Password').fill('OldPass123');
  await submitSignIn(page);
  await page.waitForURL((url) => url.pathname === '/settings');

  await page.getByRole('link', { name: 'Change password' }).click();
  await page.getByLabel(/^Current password/).fill('WrongPass123');
  await page.getByLabel(/^New password/).fill('NewPass456');
  await page.getByLabel(/^Confirm password/).fill('NewPass456');
  await page.locator('form').getByRole('button', { name: 'Change password' }).click();
  await expect(page.getByText('Your current password is incorrect.')).toBeVisible();

  await page.getByLabel(/^Current password/).fill('OldPass123');
  await page.locator('form').getByRole('button', { name: 'Change password' }).click();
  await expect(page.getByRole('status')).toContainText('other devices have been signed out');

  // This device stays signed in; the other one's session is over.
  await page.getByRole('link', { name: 'Back to account settings' }).click();
  await expect(page.getByLabel(/^Username/)).toHaveValue(username);
  expect((await request.post(`${API}/auth/refresh/`, { data: { refresh: otherDevice.refresh } })).status()).toBe(401);
  expect((await request.post(`${API}/auth/login/`, { data: { username, password: 'NewPass456' } })).ok()).toBe(true);
  await expectNoConsoleErrors(errors);
});

test.describe('on a phone, in Chinese', () => {
  test.use({ viewport: { width: 375, height: 800 } });

  test('the marketplace and auctions fit the screen and read in Chinese', async ({ page }) => {
    const errors = [];
    page.on('console', (message) => message.type() === 'error' && errors.push(message.text()));
    await page.addInitScript(() => localStorage.setItem('i18nextLng', 'zh'));

    for (const path of ['/', '/marketplace', '/auctions']) {
      await page.goto(path);
      await expect(page.locator('html')).toHaveAttribute('lang', 'zh-Hant');
      await expect(page.getByRole('button', { name: '選單' })).toBeVisible();
      await expect(page.locator('main, #root').first()).not.toBeEmpty();
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
      expect(overflow, `${path} scrolls sideways`).toBeLessThanOrEqual(0);
    }
    await expectNoConsoleErrors(errors);
  });
});
