import { expect, test } from '@playwright/test';
import { API, DEMO_PASSWORD, expectNoConsoleErrors, signIn, useEnglish } from './helpers';

// A species that isn't in the list can still be posted, but the listing stays off the marketplace
// until staff review the species (the admin side is covered by the backend tests).
test('a listing with an unlisted species waits for review and only its seller sees it', async ({ page, request }) => {
  const errors = [];
  page.on('console', (message) => message.type() === 'error' && errors.push(message.text()));
  await useEnglish(page);
  const title = `E2E Blue Tongue Skink ${Date.now()}`;
  const species = `Northern Blue-tongued Skink ${Date.now()}`;

  await signIn(page, 'tina_turtles', '/postinput');
  await page.getByLabel('Listing Title').fill(title);
  await page.getByLabel('Description').fill('Captive bred. End-to-end test listing.');
  await page.getByLabel('Price').fill('6000');
  await page.getByLabel('Species').fill(species);
  await expect(page.getByText(/isn't in our species list yet/)).toBeVisible();
  await page.getByRole('option', { name: /we'll review it/ }).click();
  await expect(page.getByRole('listbox')).toHaveCount(0);
  await page.getByLabel('Location').selectOption({ label: 'Taipei City' });
  await page.getByRole('checkbox').last().check();
  await page.getByRole('button', { name: 'Publish listing' }).click();
  await expect(page.getByRole('heading', { name: 'Your listing is waiting for review' })).toBeVisible();

  // Not on the marketplace for anyone else (asked with a buyer's token: without one, the dev backend
  // treats the request as its superuser)...
  const { access } = await (await request.post(`${API}/auth/login/`, {
    data: { username: 'buyer_hsu', password: DEMO_PASSWORD },
  })).json();
  const search = await (await request.get(`${API}/posts/live-animals/?search=${encodeURIComponent(title)}`, {
    headers: { Authorization: `Bearer ${access}` },
  })).json();
  expect(search.count).toBe(0);

  // ...but the seller sees it, marked as waiting on the species review.
  await page.getByRole('link', { name: 'View listing' }).click();
  await expect(page.getByRole('heading', { name: title })).toBeVisible();
  await expect(page.getByText(/our team is reviewing the species/)).toBeVisible();
  await page.goto('/my-listings');
  await expect(page.locator('.my-listings-row', { hasText: title }).getByText('Species under review')).toBeVisible();

  await expectNoConsoleErrors(errors);
});
