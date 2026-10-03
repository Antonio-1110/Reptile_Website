import { expect, test } from '@playwright/test';
import { API, DEMO_PASSWORD, signInWithApi, useEnglish } from './helpers';

// Price drops on saved listings reach the buyer as a site alert (issue #59), shown with a count on
// "My account" until the Alerts page has been opened.
async function token(request, username) {
  const response = await request.post(`${API}/auth/login/`, { data: { username, password: DEMO_PASSWORD } });
  expect(response.ok()).toBe(true);
  return (await response.json()).access;
}

test('a price drop on a saved listing shows up as an alert', async ({ page, request }) => {
  const buyer = 'buyer_hsu';
  const listings = await (await request.get(`${API}/posts/live-animals/`)).json();
  const listing = listings.results.find((item) => item.price && item.seller.username !== buyer);
  const buyerToken = await token(request, buyer);
  const saved = await request.post(`${API}/posts/live-animals/${listing.id}/favorite/`, { headers: { Authorization: `Bearer ${buyerToken}` } });
  expect(saved.ok()).toBe(true);
  const sellerToken = await token(request, listing.seller.username);
  const lowered = await request.patch(`${API}/posts/live-animals/${listing.id}/`, {
    headers: { Authorization: `Bearer ${sellerToken}` },
    data: { price: String(Math.floor(Number(listing.price) - 100)) },
  });
  expect(lowered.ok()).toBe(true);

  await useEnglish(page);
  await signInWithApi(page, request, buyer);
  await page.goto('/marketplace');
  const menu = page.getByRole('button', { name: /My account.*unread alert/ });
  await expect(menu).toBeVisible();
  await menu.click();
  await page.getByRole('link', { name: /^Alerts/ }).click();
  await expect(page).toHaveURL(/\/alerts$/);
  await expect(page.getByRole('heading', { name: `New Price drop: ${listing.title}` })).toBeVisible();

  // Opening the page read them, so the count is gone; the alert links back to the listing.
  await expect(page.getByRole('button', { name: /My account.*unread alert/ })).toHaveCount(0);
  await page.getByRole('link', { name: 'Open' }).first().click();
  await expect(page).toHaveURL(new RegExp(`/posts/${listing.id}$`));
});
