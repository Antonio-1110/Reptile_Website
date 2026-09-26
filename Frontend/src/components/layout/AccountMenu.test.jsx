import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { describe, expect, it, vi } from 'vitest';
import AccountMenu from './AccountMenu';

const openMenu = () => fireEvent.click(screen.getByRole('button', { name: /My account/ }));

describe('AccountMenu', () => {
  it('keeps the account pages behind one button', () => {
    render(<AccountMenu onSignOut={() => {}} />, { wrapper: MemoryRouter });
    expect(screen.queryByRole('link', { name: 'My listings' })).not.toBeInTheDocument();
    openMenu();
    expect(screen.getByRole('button', { name: /My account/ })).toHaveAttribute('aria-expanded', 'true');
    const hrefs = screen.getAllByRole('link').map((link) => link.getAttribute('href'));
    expect(hrefs).toEqual(['/my-listings', '/orders', '/saved', '/saved-searches', '/settings']);
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
});
