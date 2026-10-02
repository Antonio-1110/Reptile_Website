import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { describe, expect, it, vi } from 'vitest';
import Header from './Header';

vi.mock('../../api/authApi', async (importOriginal) => ({ ...(await importOriginal()), isLoggedIn: () => false }));

const renderAt = (path) => render(<Header onSearch={() => {}} />, {
  wrapper: ({ children }) => <MemoryRouter initialEntries={[path]}>{children}</MemoryRouter>,
});

describe('Header search button', () => {
  it('says Search on the marketplace, where it filters the results in place', () => {
    renderAt('/marketplace?category=equipment');
    expect(screen.getByRole('button', { name: 'Search' })).toHaveAttribute('type', 'submit');
  });

  it('says where it goes on every other page', () => {
    for (const path of ['/', '/auctions', '/posts/3']) {
      const { unmount } = renderAt(path);
      expect(screen.getByRole('button', { name: 'Go to marketplace' })).toHaveAttribute('type', 'submit');
      expect(screen.queryByRole('button', { name: 'Search' })).not.toBeInTheDocument();
      unmount();
    }
  });
});
