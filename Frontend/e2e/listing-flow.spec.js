import { expect, test } from '@playwright/test';
import { API, PNG, expectNoConsoleErrors, signIn, signOut, submitSignIn, useEnglish } from './helpers';

// The core loop of the marketplace: a seller lists an animal with a photo, a buyer finds it and asks
// the seller to get in touch.
test('seller lists an animal with a photo; a buyer views it and contacts the seller', async ({ page, request }) => {
  const errors = [];
  page.on('console', (message) => message.type() === 'error' && errors.push(message.text()));
  await useEnglish(page);
  const title = `E2E Pastel Ball Python ${Date.now()}`;

  // Seller: kevin_chen is a hobbyist with free listing slots.
  await signIn(page, 'kevin_chen', '/postinput');
  await expect(page.getByText(/of 5 listing slots remaining/)).toBeVisible();
  await page.locator('.media-file-input').setInputFiles(PNG);
  await expect(page.locator('.media-item')).toHaveCount(1);
  await page.getByLabel('Listing Title').fill(title);
  await page.getByLabel('Description').fill('Eats frozen/thawed, handled weekly. End-to-end test listing.');
  await page.getByLabel('Price').fill('4200');
  await page.getByLabel('Species').fill('Ball');
  await page.getByRole('option', { name: 'Ball Pythons' }).click();
  await page.getByLabel('Location').selectOption({ label: 'Taipei City' });
  await page.getByRole('checkbox').last().check();
  await page.getByRole('button', { name: 'Publish Listing' }).click();
  await expect(page.locator('.listing-editor-result--success')).toBeVisible();

  // The listing exists, with the uploaded photo as its cover.
  const search = await (await request.get(`${API}/posts/live-animals/?search=${encodeURIComponent(title)}`)).json();
  expect(search.count).toBe(1);
  const listing = search.results[0];
  expect(listing.image).toContain('/media/listings/');

  // Buyer: finds it in the marketplace, opens it and sends their details to the seller.
  await signOut(page);
  await signIn(page, 'buyer_hsu', `/marketplace`);
  await page.getByPlaceholder(/Search species/).fill(title);
  await page.getByRole('button', { name: 'Search', exact: true }).click();
  await page.getByText(title).first().click();
  await page.waitForURL(`**/posts/${listing.id}`);
  await expect(page.getByRole('heading', { name: title })).toBeVisible();
  await expect(page.locator('.listing-detail-hero-image')).toHaveAttribute('src', listing.image);

  await page.getByRole('button', { name: 'Contact seller' }).click();
  await expect(page.getByText('Send your contact details to the seller')).toBeVisible();
  await page.getByRole('button', { name: 'Send my details' }).click();
  await expect(page.getByText('Your details were sent')).toBeVisible();

  await expectNoConsoleErrors(errors);
});

test('a wrong password is refused and the right one signs in', async ({ page }) => {
  await useEnglish(page);
  await page.goto('/signin');
  await page.getByLabel('Username').fill('buyer_hsu');
  await page.getByLabel('Password').fill('not-the-password');
  await submitSignIn(page);
  await expect(page.getByRole('alert')).toHaveText('Incorrect username or password.');

  await page.getByLabel('Password').fill('DemoPass123!');
  await submitSignIn(page);
  await page.waitForURL((url) => !url.pathname.startsWith('/signin'));
  expect(await page.evaluate(() => Boolean(localStorage.getItem('accessToken')))).toBe(true);
});
