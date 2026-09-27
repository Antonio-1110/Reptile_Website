import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import InquiriesPage from './InquiriesPage';

const json = (body, status = 200) => new Response(JSON.stringify(body), { status });
const at = (url) => ({ wrapper: ({ children }) => <MemoryRouter initialEntries={[url]}>{children}</MemoryRouter> });

const inquiry = (overrides = {}) => ({
  id: 7,
  role: 'seller',
  listing: { id: 3, category: 'live_animal', title: 'Pied ball python', image: '' },
  seller: { id: 1, username: 'seller', display_name: 'Lin' },
  buyer: { username: 'buyer', phone: '0987654321' },
  created_at: '2026-09-27T10:00:00Z',
  replied_at: null,
  ...overrides,
});

describe('InquiriesPage', () => {
  beforeEach(() => localStorage.setItem('accessToken', 'token'));
  afterEach(() => {
    vi.unstubAllGlobals();
    localStorage.clear();
  });

  it("shows a received inquiry with the buyer's details and marks it replied", async () => {
    const fetchMock = vi.fn(async (url, options) => (options?.method === 'POST'
      ? json(inquiry({ replied_at: '2026-09-27T11:00:00Z' }))
      : json({ results: [inquiry()], count: 1, next: null })));
    vi.stubGlobal('fetch', fetchMock);
    render(<InquiriesPage />, at('/inquiries?role=seller'));

    expect(await screen.findByRole('link', { name: 'Pied ball python' })).toHaveAttribute('href', '/posts/3');
    expect(screen.getByText('0987654321')).toBeInTheDocument();
    expect(new URL(fetchMock.mock.calls[0][0]).searchParams.get('role')).toBe('seller');

    fireEvent.click(screen.getByRole('button', { name: 'Mark as replied' }));
    expect(await screen.findByRole('status')).toHaveTextContent("We've let the buyer know.");
    expect(fetchMock.mock.calls[1][0]).toMatch(/\/posts\/inquiries\/7\/replied\/$/);
    expect(screen.queryByRole('button', { name: 'Mark as replied' })).not.toBeInTheDocument();
  });

  it('shows a sent inquiry with who it went to and whether they replied', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => json({
      results: [inquiry({ role: 'buyer', buyer: null, listing: { id: 4, category: 'equipment', title: 'Heat mat', image: '' } })],
      count: 1,
      next: null,
    })));
    render(<InquiriesPage />, at('/inquiries?role=buyer'));

    expect(await screen.findByRole('link', { name: 'Heat mat' })).toHaveAttribute('href', '/equipment/4');
    expect(screen.getByRole('link', { name: 'Sent to Lin' })).toHaveAttribute('href', '/sellers/1');
    expect(screen.getByText('Waiting for the seller to get in touch')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Mark as replied' })).not.toBeInTheDocument();
  });

  it('says what to do when there are none', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => json({ results: [], count: 0, next: null })));
    render(<InquiriesPage />, at('/inquiries?role=buyer'));
    expect(await screen.findByText(/haven't contacted any sellers yet/)).toBeInTheDocument();
  });
});
