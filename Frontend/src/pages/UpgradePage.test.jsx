import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import UpgradePage from './UpgradePage';
import { setFeatures } from '../hooks/useFeature';

const json = (body) => new Response(JSON.stringify(body), { status: 200 });
const plan = (id, overrides = {}) => ({
  id, max_post_count: 5, max_images_per_post: 3, can_start_auction: false, auction_fee_rate: null,
  monthly_price: null, currency: 'TWD', ...overrides,
});

function renderWithPlans(feeRate, profile = {}) {
  vi.stubGlobal('fetch', vi.fn(async (url) => (String(url).includes('/account/plans/')
    ? json([
      plan('hobbyist'),
      plan('commercial_paid', { can_start_auction: true, auction_fee_rate: feeRate, monthly_price: '499.00' }),
    ])
    : json({ username: 'gecko_mei', account_type: 'hobbyist', is_paid_account: false, launch_offer_ends_at: null, ...profile }))));
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

  it('shows paid plans as free for now, since staff grant them by email', async () => {
    renderWithPlans('0.03');
    expect(await screen.findByText('Free for now')).toBeInTheDocument();
    expect(screen.getByText('Free')).toBeInTheDocument();
    expect(screen.queryByText(/NT\$|a month/)).not.toBeInTheDocument();
  });

  it('tells early sellers when their launch offer ends', async () => {
    renderWithPlans('0.03', { launch_offer_ends_at: '2027-03-29T08:00:00Z' });
    expect(await screen.findByText(/Early seller offer: auctions you start before March 29, 2027 have no fee/)).toBeInTheDocument();
  });

  it('says nothing about a launch offer to sellers without one', async () => {
    renderWithPlans('0.03');
    await screen.findByText('Free for now');
    expect(screen.queryByText(/Early seller offer/)).not.toBeInTheDocument();
  });

  it('asks sellers to email support to switch plans, with their username', async () => {
    renderWithPlans('0.03');
    fireEvent.click(await screen.findByRole('button', { name: 'Choose this plan' }));
    expect(screen.getByRole('status')).toHaveTextContent('Switching to Commercial Pro');
    expect(screen.getByRole('status')).toHaveTextContent('include your username (gecko_mei)');
    const link = screen.getByRole('link', { name: /@/ });
    expect(link.getAttribute('href')).toMatch(/^mailto:[^?]+@[^?]+\?subject=Switch%20gecko_mei%20to%20Commercial%20Pro$/);
  });

  it('says nothing about auctions while they are switched off', async () => {
    setFeatures({ auctions: false });
    renderWithPlans('0', { launch_offer_ends_at: '2027-03-29T08:00:00Z' });
    await screen.findByText('Free for now');
    expect(screen.getByText('Commercial accounts can list more animals and show more photos.')).toBeInTheDocument();
    expect(screen.queryByText(/auction/i)).not.toBeInTheDocument();
  });
});
