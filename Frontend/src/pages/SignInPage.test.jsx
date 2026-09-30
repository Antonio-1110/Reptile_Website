import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { describe, expect, it } from 'vitest';
import SignInPage from './SignInPage';

function renderAt(entry) {
  render(<SignInPage />, { wrapper: ({ children }) => <MemoryRouter initialEntries={[entry]}>{children}</MemoryRouter> });
}

describe('SignInPage', () => {
  it("doesn't tell someone who chose to sign in that they'll be taken back", () => {
    renderAt('/signin?next=%2Fmarketplace');
    expect(screen.getByRole('heading', { name: 'Welcome back' })).toBeInTheDocument();
    expect(screen.queryByRole('status')).not.toBeInTheDocument();
  });

  it('tells a visitor who was sent here that they will go back afterwards', () => {
    renderAt({ pathname: '/signin', search: '?next=%2Fsettings', state: { signInRequired: true } });
    expect(screen.getByRole('status')).toHaveTextContent("we'll take you back");
  });
});
