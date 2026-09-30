import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import AlertsPage from './AlertsPage';
import { getAlertsPage, markAllAlertsRead } from '../../api/alertsApi';
import { ALERTS_CHANGED } from '../../components/layout/AccountMenu';

vi.mock('../../api/alertsApi', () => ({ getAlertsPage: vi.fn(), markAllAlertsRead: vi.fn(() => Promise.resolve({})), getUnreadAlertCount: vi.fn() }));
vi.mock('../../api/listingsApi', async (importOriginal) => ({ ...(await importOriginal()), isLoggedIn: () => true }));

const alert = (id, isRead, fields = {}) => ({
  id, title: `Alert ${id}`, body: 'Price is now $8,000', link: '/posts/3', createdAt: new Date('2026-09-30T10:00:00Z'), isRead, ...fields,
});

describe('AlertsPage', () => {
  beforeEach(() => vi.clearAllMocks());

  it('lists alerts, tags the new ones and marks them read', async () => {
    getAlertsPage.mockResolvedValue({ results: [alert(1, false), alert(2, true, { link: '' })], hasMore: false });
    const changed = vi.fn();
    window.addEventListener(ALERTS_CHANGED, changed);
    render(<AlertsPage />, { wrapper: MemoryRouter });

    expect(await screen.findByRole('heading', { name: /New.*Alert 1/ })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Alert 2' })).toBeInTheDocument();
    expect(screen.getAllByRole('link', { name: 'Open' })).toHaveLength(1);
    expect(markAllAlertsRead).toHaveBeenCalledTimes(1);
    await vi.waitFor(() => expect(changed).toHaveBeenCalled());
    window.removeEventListener(ALERTS_CHANGED, changed);
  });

  it('does not mark anything when everything is already read', async () => {
    getAlertsPage.mockResolvedValue({ results: [alert(2, true)], hasMore: false });
    render(<AlertsPage />, { wrapper: MemoryRouter });
    await screen.findByRole('heading', { name: 'Alert 2' });
    expect(markAllAlertsRead).not.toHaveBeenCalled();
  });

  it('shows an empty state and an error with a retry', async () => {
    getAlertsPage.mockResolvedValueOnce({ results: [], hasMore: false });
    const { unmount } = render(<AlertsPage />, { wrapper: MemoryRouter });
    expect(await screen.findByText(/No alerts yet/)).toBeInTheDocument();
    unmount();

    getAlertsPage.mockRejectedValueOnce(new Error(''));
    render(<AlertsPage />, { wrapper: MemoryRouter });
    expect(await screen.findByRole('alert')).toHaveTextContent("Couldn't load your alerts.");
    expect(screen.getByRole('button', { name: 'Try again' })).toBeInTheDocument();
  });
});
