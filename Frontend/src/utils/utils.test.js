import { describe, expect, it } from 'vitest';
import i18n from '../i18n';
import { formatDuration, formatMoney, getAuctionPhase, getHeadlinePrice } from './auctionFormat';
import { errorText, toErrorState } from './errorState';
import { buildMarketplaceUrl, readMarketplaceSearch } from './marketplaceSearch';

const t = i18n.t.bind(i18n);

describe('formatMoney', () => {
  it('formats per language and shows cents only when there are any', () => {
    expect(formatMoney('5000.00', 'TWD', 'en')).toBe('NT$5,000');
    expect(formatMoney('5000.50', 'TWD', 'en')).toBe('NT$5,000.50');
    expect(formatMoney('5000', 'TWD', 'zh')).toBe('$5,000');
    expect(formatMoney(null, 'TWD', 'en')).toBe('');
  });
});

describe('auction phase and headline price', () => {
  const now = Date.parse('2026-09-25T12:00:00Z');
  const auction = (fields) => ({
    status: 'active', startsAt: new Date(now - 3600e3), endsAt: new Date(now + 3600e3),
    startingPrice: '5000', currentPrice: null, winningBidAmount: null, soldVia: null, ...fields,
  });

  it('works out the phase from the times, not only the stored status', () => {
    expect(getAuctionPhase(auction(), now)).toBe('live');
    expect(getAuctionPhase(auction({ startsAt: new Date(now + 1) }), now)).toBe('upcoming');
    expect(getAuctionPhase(auction({ endsAt: new Date(now) }), now)).toBe('ended'); // before close_auctions runs
    expect(getAuctionPhase(auction({ status: 'cancelled' }), now)).toBe('cancelled');
  });

  it('shows the starting, current, winning or buy-now price', () => {
    expect(getHeadlinePrice(auction(), 'live')).toEqual({ labelKey: 'auctions.price.startingBid', amount: '5000' });
    expect(getHeadlinePrice(auction({ currentPrice: '5100' }), 'live').labelKey).toBe('auctions.price.currentBid');
    expect(getHeadlinePrice(auction({ currentPrice: '5100' }), 'ended').labelKey).toBe('auctions.price.winningBid');
    expect(getHeadlinePrice(auction({ soldVia: 'buy_now', soldPrice: '9000' }), 'ended'))
      .toEqual({ labelKey: 'auctions.price.boughtNow', amount: '9000' });
  });

  it('formats durations at the right precision', () => {
    expect(formatDuration(t, (2 * 86400 + 4 * 3600) * 1000)).toBe('2d 4h');
    expect(formatDuration(t, (3 * 3600 + 12 * 60) * 1000)).toBe('3h 12m');
    expect(formatDuration(t, (4 * 60 + 5) * 1000)).toBe('4m 05s');
    expect(formatDuration(t, -1000)).toBe('0m 00s');
  });
});

describe('marketplace search in the URL', () => {
  it('round-trips the search term and tags', () => {
    const tags = [{ type: 'species', value: 'Ball Pythons' }, { type: 'morph', value: 'Pastel' }, { type: 'morph', value: 'Pied' }];
    const url = buildMarketplaceUrl(' pied ', tags);
    expect(url).toBe('/marketplace?search=pied&species=Ball+Pythons&genes=Pastel%2CPied');
    expect(readMarketplaceSearch(url.split('?')[1])).toEqual({ term: 'pied', tags });
    expect(buildMarketplaceUrl('', [])).toBe('/marketplace');
  });
});

describe('error state', () => {
  it("keeps the server's message, or a key to translate later", () => {
    expect(errorText(t, toErrorState(new Error('Server says no'), 'listings.loadError'))).toBe('Server says no');
    expect(errorText(t, toErrorState({}, 'listings.loadError'))).toBe(t('listings.loadError'));
    expect(errorText(t, null)).toBe('');
  });
});
