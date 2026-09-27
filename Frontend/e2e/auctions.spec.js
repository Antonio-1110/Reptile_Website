import { expect, test } from '@playwright/test';
import { expectNoConsoleErrors, findAuction, signIn, signInWithApi, signOut, useEnglish } from './helpers';

// Payments are instant here (the e2e backend runs with DEBUG on, so InstantPaymentGateway), which lets
// a whole sale run in one test.

test('two buyers bid against each other and each sees whether they lead', async ({ page, request }) => {
  const errors = [];
  page.on('console', (message) => message.type() === 'error' && errors.push(message.text()));
  await useEnglish(page);
  const auction = await findAuction(request, (candidate) => !candidate.buy_now_price && candidate.bid_count > 0);
  const listingPath = `/posts/${auction.listing.id}`;

  const bid = async (username) => {
    if (page.url().startsWith('http')) await signOut(page);
    await signIn(page, username, listingPath);
    // Some demo buyers already hold a deposit on this auction from the seeded bids.
    const payDeposit = page.getByRole('button', { name: /^Pay .* deposit$/ });
    await expect(payDeposit.or(page.getByRole('button', { name: 'Place bid' }))).toBeVisible();
    if (await payDeposit.isVisible()) {
      await payDeposit.click();
      await expect(page.getByText('Deposit paid — you can bid now.')).toBeVisible();
    }
    await page.getByRole('button', { name: 'Place bid' }).click();
    await page.getByRole('button', { name: 'Confirm bid' }).click();
    await expect(page.getByText("You're the highest bidder.")).toBeVisible();
  };

  await bid('buyer_amy');
  await bid('buyer_jason');

  await signOut(page);
  await signIn(page, 'buyer_amy', listingPath);
  await expect(page.getByText("You've been outbid.")).toBeVisible();

  const bids = await (await request.get(`http://127.0.0.1:8001/api/v1/auctions/${auction.id}/bids/`)).json();
  expect((bids.results ?? bids).length).toBe(auction.bid_count + 2);
  await expectNoConsoleErrors(errors);
});

test.describe('on a phone, in Chinese', () => {
  const PHONE = { width: 375, height: 800 };

  // Each person gets their own browser context: a phone, the UI in Chinese, already signed in.
  async function openAs(browser, request, username, errors) {
    const context = await browser.newContext({ viewport: PHONE });
    const page = await context.newPage();
    page.on('console', (message) => message.type() === 'error' && errors.push(message.text()));
    await page.addInitScript(() => localStorage.setItem('i18nextLng', 'zh'));
    await signInWithApi(page, request, username);
    return page;
  }

  async function expectNoSidewaysScroll(page) {
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
    expect(overflow).toBeLessThanOrEqual(0);
  }

  test('a buyer buys now, the seller hands the animal over and the buyer completes the sale', async ({ browser, request }) => {
    const errors = [];
    const auction = await findAuction(request, (candidate) => candidate.buy_now_available && candidate.bid_count === 0);
    const listingPath = `/posts/${auction.listing.id}`;

    const buyer = await openAs(browser, request, 'buyer_amy', errors);
    await buyer.goto(listingPath);
    await expectNoSidewaysScroll(buyer);
    await buyer.getByRole('button', { name: /^以 .* 直接購買$/ }).click();
    await buyer.getByRole('button', { name: /^支付 \S+$/ }).click();
    await expect(buyer.getByText('已收到款項，這隻個體是你的了！')).toBeVisible();

    const seller = await openAs(browser, request, auction.seller.username, errors);
    await seller.goto(listingPath);
    await seller.getByRole('button', { name: '我已交貨／寄出' }).click();
    await expect(seller.getByRole('button', { name: '我已交貨／寄出' })).toHaveCount(0);
    await expectNoSidewaysScroll(seller);

    await buyer.reload();
    await buyer.getByRole('button', { name: '已收到，個體健康' }).click();
    await buyer.getByRole('button', { name: '確認，完成交易' }).click();
    await expect(buyer.getByText('交易完成，謝謝！')).toBeVisible();

    const closed = await (await request.get(`http://127.0.0.1:8001/api/v1/auctions/${auction.id}/`)).json();
    expect(closed.sold_via).toBe('buy_now');
    await expectNoConsoleErrors(errors);
  });
});
