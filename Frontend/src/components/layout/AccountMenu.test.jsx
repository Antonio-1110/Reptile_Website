import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { describe, expect, it, vi } from 'vitest';
import AccountMenu, { INQUIRIES_CHANGED } from './AccountMenu';
import { getWaitingInquiryCount } from '../../api/listingsApi';

vi.mock('../../api/listingsApi', () => ({ getWaitingInquiryCount: vi.fn(() => Promise.resolve(0)) }));

const openMenu = () => fireEvent.click(screen.getByRole('button', { name: /My account/ }));

describe('AccountMenu', () => {
  it('keeps the account pages behind one button', () => {
    render(<AccountMenu onSignOut={() => {}} />, { wrapper: MemoryRouter });
    expect(screen.queryByRole('link', { name: 'My listings' })).not.toBeInTheDocument();
    openMenu();
    expect(screen.getByRole('button', { name: /My account/ })).toHaveAttribute('aria-expanded', 'true');
    const hrefs = screen.getAllByRole('link').map((link) => link.getAttribute('href'));
    expect(hrefs).toEqual(['/my-listings', '/orders', '/inquiries', '/saved', '/saved-searches', '/settings']);
  });

  it('signs out from the menu', () => {
    const onSignOut = vi.fn();
    render(<AccountMenu onSignOut={onSignOut} />, { wrapper: MemoryRouter });
    openMenu();
    fireEvent.click(screen.getByRole('button', { name: 'Sign out' }));
    expect(onSignOut).toHaveBeenCalled();
  });

  it('closes on Escape and after picking a page', () => {
    render(<AccountMenu onSignOut={() => {}} />, { wrapper: MemoryRouter });
    openMenu();
    fireEvent.keyDown(document, { key: 'Escape' });
    expect(screen.queryByRole('link', { name: 'My orders' })).not.toBeInTheDocument();
    openMenu();
    fireEvent.click(screen.getByRole('link', { name: 'My orders' }));
    expect(screen.queryByRole('link', { name: 'My orders' })).not.toBeInTheDocument();
  });

  it('shows how many inquiries are waiting for a reply, and updates when one is marked replied', async () => {
    getWaitingInquiryCount.mockResolvedValueOnce(2).mockResolvedValueOnce(1);
    render(<AccountMenu onSignOut={() => {}} />, { wrapper: MemoryRouter });
    expect(await screen.findByRole('button', { name: /My account.*2 inquiries waiting for your reply/ })).toBeInTheDocument();
    openMenu();
    expect(screen.getByRole('link', { name: /Inquiries.*2 inquiries waiting/ })).toHaveAttribute('href', '/inquiries');

    window.dispatchEvent(new Event(INQUIRIES_CHANGED));
    expect(await screen.findByRole('link', { name: /Inquiries.*1 inquiry waiting for your reply/ })).toBeInTheDocument();
  });

  it('shows no badge when nothing is waiting', async () => {
    render(<AccountMenu onSignOut={() => {}} />, { wrapper: MemoryRouter });
    await vi.waitFor(() => expect(getWaitingInquiryCount).toHaveBeenCalled());
    expect(screen.getByRole('button', { name: /My account/ }).textContent).not.toMatch(/\d/);
  });
});
