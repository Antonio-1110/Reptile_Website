import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter, useLocation } from 'react-router';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import App from './App';

// The pages fetch their own data; stand-ins that show which page rendered, with what, are enough
// to test the routing.
vi.mock('./pages/HomePage', () => ({ default: () => <p>home page</p> }));
vi.mock('./pages/MarketplacePage', () => ({
  default: ({ searchTerm, searchTags }) => <p>marketplace: {searchTerm} {searchTags.map((tag) => tag.value).join(',')}</p>,
}));
vi.mock('./pages/ListingDetail/ListingDetailPage', () => ({
  default: ({ listingId, category = 'live_animal' }) => <p>listing {category} {listingId}</p>,
}));
vi.mock('./pages/SellerProfilePage', () => ({ default: ({ sellerId }) => <p>seller {sellerId}</p> }));
vi.mock('./pages/AccountSettingsPage', () => ({ default: () => <p>settings page</p> }));
vi.mock('./pages/SignInPage', () => ({ default: () => <p>sign-in page</p> }));
vi.mock('./pages/Auctions/AuctionsPage', () => ({ default: () => <p>auctions page</p> }));
vi.mock('./pages/ListingEditor/ListingEditorPage', () => ({
  default: ({ editId, editCategory }) => <p>editor {editId} {editCategory}</p>,
}));

function CurrentUrl() {
  const location = useLocation();
  return <output aria-label="url">{location.pathname + location.search}</output>;
}

function renderAt(url) {
  return render(
    <MemoryRouter initialEntries={[url]}>
      <App />
      <CurrentUrl />
    </MemoryRouter>,
  );
}

const signIn = () => localStorage.setItem('accessToken', 'token');

describe('App routing', () => {
  // jsdom has no scrolling; App scrolls to the top on each new page.
  beforeEach(() => vi.spyOn(window, 'scrollTo').mockImplementation(() => {}));

  it('passes numeric ids from the path to the page', () => {
    renderAt('/posts/12');
    expect(screen.getByText('listing live_animal 12')).toBeInTheDocument();
  });

  it('opens equipment listings as equipment', () => {
    renderAt('/equipment/7');
    expect(screen.getByText('listing equipment 7')).toBeInTheDocument();
  });

  it('shows the home page for unknown paths and non-numeric ids', () => {
    renderAt('/sellers/abc');
    expect(screen.getByText('home page')).toBeInTheDocument();
  });

  it('sends a signed-out visitor to sign in and back to the page they asked for', () => {
    renderAt('/postinput?edit=3&category=equipment');
    expect(screen.getByText('sign-in page')).toBeInTheDocument();
    expect(screen.getByLabelText('url')).toHaveTextContent(`/signin?next=${encodeURIComponent('/postinput?edit=3&category=equipment')}`);
  });

  it('opens protected pages when signed in, with their query', () => {
    signIn();
    renderAt('/postinput?edit=3&category=equipment');
    expect(screen.getByText('editor 3 equipment')).toBeInTheDocument();
  });

  it('reads the marketplace search from the URL', () => {
    renderAt('/marketplace?search=pied&species=Ball%20Pythons');
    expect(screen.getByText('marketplace: pied Ball Pythons')).toBeInTheDocument();
  });

  it('takes a header search from another page to the marketplace', () => {
    renderAt('/sellers/4');
    fireEvent.change(screen.getByPlaceholderText(/search/i), { target: { value: 'pastel' } });
    fireEvent.submit(screen.getByPlaceholderText(/search/i).closest('form'));
    expect(screen.getByText('marketplace: pastel')).toBeInTheDocument();
    expect(screen.getByLabelText('url')).toHaveTextContent('/marketplace?search=pastel');
  });

  it('keeps the category when searching from the marketplace', () => {
    renderAt('/marketplace?category=equipment');
    fireEvent.change(screen.getByPlaceholderText(/search/i), { target: { value: 'heat lamp' } });
    fireEvent.submit(screen.getByPlaceholderText(/search/i).closest('form'));
    expect(screen.getByLabelText('url')).toHaveTextContent('/marketplace?category=equipment&search=heat+lamp');
  });

  it('navigates without a page load when a link is clicked', () => {
    renderAt('/');
    fireEvent.click(screen.getByRole('link', { name: 'Auctions' }));
    expect(screen.getByLabelText('url')).toHaveTextContent('/auctions');
    expect(screen.getByText('auctions page')).toBeInTheDocument();
  });
});
