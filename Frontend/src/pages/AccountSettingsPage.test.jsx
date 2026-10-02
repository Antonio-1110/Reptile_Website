import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { afterEach, describe, expect, it, vi } from 'vitest';
import AccountSettingsPage from './AccountSettingsPage';

const profile = {
  username: 'gecko_shop', display_name: 'gecko_shop', email: 'shop@example.com', account_type: 'hobbyist',
  max_post_count: 5, max_images_per_post: 3, has_password: true,
  username_change_days: 30, username_change_available_at: null,
};

function renderWith(overrides) {
  vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify({ ...profile, ...overrides }))));
  render(<AccountSettingsPage />, { wrapper: ({ children }) => <MemoryRouter>{children}</MemoryRouter> });
}

describe('AccountSettingsPage sign-in and security', () => {
  afterEach(() => vi.unstubAllGlobals());

  it('explains how often the username can change', async () => {
    renderWith({});
    expect(await screen.findByText(/once every 30 days/)).toBeInTheDocument();
    expect(screen.getByLabelText(/^Username/)).not.toHaveAttribute('readonly');
    expect(screen.getByRole('link', { name: 'Change password' })).toHaveAttribute('href', '/settings/password');
  });

  it('locks the username until it may change again', async () => {
    renderWith({ username_change_available_at: '2026-10-30T12:00:00Z' });
    expect(await screen.findByText(/You can change it again on/)).toBeInTheDocument();
    expect(screen.getByLabelText(/^Username/)).toHaveAttribute('readonly');
  });

  it('offers accounts made with Google a way to set a password', async () => {
    renderWith({ has_password: false });
    expect(await screen.findByRole('link', { name: 'Set a password' })).toHaveAttribute('href', '/settings/password');
  });
});
