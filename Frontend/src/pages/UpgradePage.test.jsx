import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import UpgradePage from './UpgradePage';

const json = (body) => new Response(JSON.stringify(body), { status: 200 });
const plan = (id, overrides = {}) => ({
  id, max_post_count: 5, max_images_per_post: 3, can_start_auction: false, auction_fee_rate: null, ...overrides,
});

function renderWithPlans(feeRate) {
  vi.stubGlobal('fetch', vi.fn(async (url) => (String(url).includes('/account/plans/')
    ? json([plan('hobbyist'), plan('commercial_paid', { can_start_auction: true, auction_fee_rate: feeRate })])
    : json({ account_type: 'hobbyist', is_paid_account: false }))));
  render(<UpgradePage />, { wrapper: ({ children }) => <MemoryRouter>{children}</MemoryRouter> });
}

describe('UpgradePage', () => {
  beforeEach(() => localStorage.setItem('accessToken', 'token'));
  afterEach(() => {
    vi.unstubAllGlobals();
    localStorage.clear();
  });

  it('advertises free auction sales while the fee is 0, only on plans that run auctions', async () => {
    renderWithPlans('0');
    expect(await screen.findByText('0% fee on auction sales for now')).toBeInTheDocument();
    expect(screen.getAllByText(/fee on auction sales/)).toHaveLength(1);
  });

  it('shows the fee as a percentage once there is one', async () => {
    renderWithPlans('0.05');
    expect(await screen.findByText('5% fee on auction sales')).toBeInTheDocument();
  });
});
