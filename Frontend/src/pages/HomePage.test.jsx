import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import HomePage from './HomePage';
import { setFeatures } from '../hooks/useFeature';

function renderHome() {
  render(<HomePage />, { wrapper: ({ children }) => <MemoryRouter>{children}</MemoryRouter> });
}

describe('HomePage', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify({ count: 0, results: [] }), { status: 200 })));
    vi.stubGlobal('ResizeObserver', class { observe() {} disconnect() {} });
  });
  afterEach(() => vi.unstubAllGlobals());

  it('says why to list here instead of in LINE and Facebook groups', async () => {
    renderHome();
    expect(screen.getByRole('heading', { name: "Listings that don't get buried" })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Made for selling animals' })).toBeInTheDocument();
    await screen.findByText('No listings yet');
  });

  it('leaves auctions out while they are switched off', async () => {
    setFeatures({ auctions: false });
    renderHome();
    await screen.findByText('No listings yet');
    expect(screen.queryByText(/auction/i)).not.toBeInTheDocument();
  });

  it('mentions auctions once they are switched on', async () => {
    setFeatures({ auctions: true });
    renderHome();
    await screen.findByText('No listings yet');
    expect(screen.getByRole('heading', { name: 'Auctions you can trust' })).toBeInTheDocument();
    expect(screen.getByText(/bid in an auction/)).toBeInTheDocument();
  });
});
