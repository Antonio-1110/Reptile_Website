import { expect, test } from '@playwright/test';
import { expectNoConsoleErrors, useEnglish } from './helpers';

// Links move between pages without reloading the app, and the URL (Back included) stays the source
// of truth for what a page shows.
test('browsing moves between pages client-side and Back restores the marketplace category', async ({ page }) => {
  const errors = [];
  page.on('console', (message) => message.type() === 'error' && errors.push(message.text()));
  await useEnglish(page);
  await page.goto('/');
  // Gone after any full page load, so it proves the navigation below happened in the app.
  await page.evaluate(() => { window.stillSamePage = true; });

  await page.getByRole('link', { name: 'Browse the marketplace' }).click();
  await expect(page).toHaveURL(/\/marketplace$/);
  await page.getByRole('radio', { name: 'Equipment' }).click();
  await expect(page).toHaveURL(/\/marketplace\?category=equipment$/);

  await page.locator('.card-title-link').first().click();
  await expect(page).toHaveURL(/\/equipment\/\d+$/);
  await expect(page.locator('.listing-detail-back')).toBeVisible();

  await page.goBack();
  await expect(page).toHaveURL(/\/marketplace\?category=equipment$/);
  await expect(page.getByRole('radio', { name: 'Equipment' })).toHaveAttribute('aria-checked', 'true');

  await page.getByRole('link', { name: 'Auctions' }).click();
  await expect(page).toHaveURL(/\/auctions$/);
  expect(await page.evaluate(() => window.stillSamePage)).toBe(true);
  await expectNoConsoleErrors(errors);
});

test('a signed-out visitor opening a members-only page is sent to sign in first', async ({ page }) => {
  await useEnglish(page);
  await page.goto('/settings');
  await expect(page).toHaveURL(`/signin?next=${encodeURIComponent('/settings')}`);
});
