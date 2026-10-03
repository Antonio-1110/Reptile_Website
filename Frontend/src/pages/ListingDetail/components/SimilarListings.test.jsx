import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { describe, expect, it, vi } from 'vitest';
import SimilarListings from './SimilarListings';
import { getSimilarListings } from '../../../api/listingsApi';

vi.mock('../../../api/listingsApi', async (importOriginal) => ({ ...(await importOriginal()), getSimilarListings: vi.fn() }));

const listing = { id: 5, title: 'Pied Ball Python', image: '', genes: ['Pied'], location: 'taipei', price: '3000.00', seller: 'Apex', sellerTag: 'apex' };

describe('SimilarListings', () => {
  it('shows similar listings under a heading', async () => {
    getSimilarListings.mockResolvedValue([listing]);
    render(<SimilarListings listingId={1} category="live_animal" />, { wrapper: MemoryRouter });
    expect(await screen.findByRole('heading', { name: 'Similar listings' })).toBeInTheDocument();
    expect(screen.getByText('Pied Ball Python')).toBeInTheDocument();
    expect(getSimilarListings).toHaveBeenCalledWith(1, 'live_animal');
  });

  it('stays hidden when there are none or the request fails', async () => {
    getSimilarListings.mockResolvedValueOnce([]);
    const { container, unmount } = render(<SimilarListings listingId={1} category="live_animal" />, { wrapper: MemoryRouter });
    await vi.waitFor(() => expect(getSimilarListings).toHaveBeenCalled());
    expect(container).toBeEmptyDOMElement();
    unmount();

    getSimilarListings.mockRejectedValueOnce(new Error('offline'));
    const failed = render(<SimilarListings listingId={2} category="equipment" />, { wrapper: MemoryRouter });
    await vi.waitFor(() => expect(getSimilarListings).toHaveBeenCalledWith(2, 'equipment'));
    expect(failed.container).toBeEmptyDOMElement();
  });
});
