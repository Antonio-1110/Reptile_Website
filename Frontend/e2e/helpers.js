import { expect } from '@playwright/test';

export const API = 'http://127.0.0.1:8001/api/v1';
export const DEMO_PASSWORD = 'DemoPass123!'; // every seed_demo account

// A 1×1 PNG, enough for the photo upload (the backend checks it's a real image).
export const PNG = {
  name: 'photo.png',
  mimeType: 'image/png',
  buffer: Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==', 'base64'),
};

export async function signIn(page, username, next = '/marketplace') {
  await page.goto(`/signin?next=${encodeURIComponent(next)}`);
  await page.getByLabel('Username').fill(username);
  await page.getByLabel('Password').fill(DEMO_PASSWORD);
  await submitSignIn(page);
  await page.waitForURL((url) => url.pathname === next);
}

// The form's own submit button ("Sign in"), not the header's "Sign In" link or the "Sign in" tab.
export async function submitSignIn(page) {
  await page.locator('form').getByRole('button', { name: 'Sign in', exact: true }).click();
}

export async function signOut(page) {
  await page.evaluate(() => {
    localStorage.removeItem('accessToken');
    localStorage.removeItem('refreshToken');
  });
}

// Pins the UI to English so the tests can find things by their visible names.
export async function useEnglish(page) {
  await page.addInitScript(() => localStorage.setItem('i18nextLng', 'en'));
}

export async function expectNoConsoleErrors(errors) {
  expect(errors.filter((text) => !/Failed to load resource/.test(text))).toEqual([]);
}
