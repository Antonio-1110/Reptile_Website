import { afterEach, describe, expect, it, vi } from 'vitest';
import { getAuction, getLatestAuctionForListing, markHandedOver, payDeposit, placeBid } from './auctionsApi';

const json = (body) => new Response(JSON.stringify(body), { status: 200 });

function mockFetch(body) {
  const fetchMock = vi.fn(async () => json(body));
  vi.stubGlobal('fetch', fetchMock);
  return fetchMock;
}

const apiAuction = {
  id: 9, status: 'active', seller: { display_name: 'Apex Exotics' }, is_seller: false,
  listing: { id: 4, category: 'live_animal', title: 'Pied Ball Python', image: null, location: 'TPE', genes: null },
  currency: 'TWD', starting_price: '5000.00', min_increment: '100.00', deposit_amount: '500.00',
  starts_at: '2026-09-25T00:00:00Z', ends_at: '2026-09-30T00:00:00Z', bid_count: 2, current_price: '5200.00',
  minimum_next_bid: '5300.00', buy_now_price: null, buy_now_available: false, sold_via: null,
  my_deposit: { id: 1, amount: '500.00', currency: 'TWD', status: 'held', provider_reference: 'secret-ref' },
  my_purchase: null,
};

describe('auctionsApi', () => {
  afterEach(() => vi.unstubAllGlobals());

  it('maps an auction to UI names, dates and safe defaults', async () => {
    mockFetch(apiAuction);
    const auction = await getAuction(9);
    expect(auction).toMatchObject({
      id: 9, sellerName: 'Apex Exotics', isSeller: false, minimumNextBid: '5300.00', buyNowAvailable: false,
      pendingBuyNowCount: 0, saleFellThrough: false, extendWindowMinutes: 0,
      listing: { id: 4, image: '', genes: [] },
      myDeposit: { id: 1, amount: '500.00', currency: 'TWD', status: 'held' },
    });
    expect(auction.endsAt).toEqual(new Date('2026-09-30T00:00:00Z'));
    // Only the fields the UI needs are kept from the deposit.
    expect(auction.myDeposit).not.toHaveProperty('provider_reference');
  });

  it("skips cancelled auctions when finding a listing's latest one", async () => {
    const fetchMock = mockFetch({ results: [{ ...apiAuction, id: 11, status: 'cancelled' }, apiAuction] });
    const auction = await getLatestAuctionForListing(5, 'equipment');
    expect(auction.id).toBe(9);
    expect(new URL(fetchMock.mock.calls[0][0]).searchParams.get('equipment_post')).toBe('5');
  });

  it('returns null when a listing has no auction', async () => {
    mockFetch({ results: [{ ...apiAuction, status: 'cancelled' }] });
    expect(await getLatestAuctionForListing(5)).toBeNull();
  });

  it('sends bids as strings and passes on what the payment gateway needs', async () => {
    const fetchMock = mockFetch({ id: 1, amount: '5300.00', created_at: '2026-09-26T00:00:00Z', is_mine: true });
    const bid = await placeBid(9, 5300);
    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({ amount: '5300' });
    expect(bid.isMine).toBe(true);

    mockFetch({ id: 2, amount: '500.00', currency: 'TWD', status: 'pending', payment: { checkout_url: 'https://pay.example/x' } });
    const { deposit, payment } = await payDeposit(9);
    expect(deposit.status).toBe('pending');
    expect(payment).toEqual({ checkout_url: 'https://pay.example/x' });
  });

  it('posts order actions to the order endpoints', async () => {
    const fetchMock = mockFetch({ id: 3, role: 'seller', status: 'handed_over' });
    await markHandedOver(3, 'Black Cat 1234');
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toMatch(/\/v1\/auctions\/orders\/3\/handed-over\/$/);
    expect(init.method).toBe('POST');
    expect(JSON.parse(init.body)).toEqual({ note: 'Black Cat 1234' });
  });
});
