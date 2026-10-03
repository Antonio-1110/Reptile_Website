import { expect, test } from '@playwright/test';
import { expectNoConsoleErrors, useEnglish } from './helpers';

// The marketplace sort menu reorders the results on the server, and a listing's page suggests others
// like it (issue #60).
const cardPrices = (page) => page.locator('.card-container').evaluateAll((cards) => cards.map((card) => {
  const match = card.textContent.match(/\$([\d,]+)/);
  return match ? Number(match[1].replace(/,/g, '')) : null;
}).filter((price) => price !== null));

test('sorting by price reorders the marketplace', async ({ page }) => {
  const errors = [];
  page.on('console', (message) => message.type() === 'error' && errors.push(message.text()));
  await useEnglish(page);
  await page.goto('/marketplace');
  await expect(page.locator('.card-container').first()).toBeVisible();
  await expect(page.getByLabel('Sort by')).toHaveValue('recommended');

  const sorted = page.waitForResponse((response) => response.url().includes('ordering=price'));
  await page.getByLabel('Sort by').selectOption({ label: 'Price: low to high' });
  await sorted;
  await expect(async () => {
    const prices = await cardPrices(page);
    expect(prices.length).toBeGreaterThan(1);
    expect(prices).toEqual([...prices].sort((a, b) => a - b));
  }).toPass();
  await expectNoConsoleErrors(errors);
});

test('a listing page suggests similar listings that open their own page', async ({ page }) => {
  await useEnglish(page);
  await page.goto('/marketplace');
  await page.locator('.card-title-link').first().click();
  const similar = page.getByRole('region', { name: 'Similar listings' });
  await expect(similar).toBeVisible();
  const url = page.url();
  await similar.locator('.card-title-link').first().click();
  await expect(page).not.toHaveURL(url);
  await expect(page).toHaveURL(/\/posts\/\d+$/);
});
