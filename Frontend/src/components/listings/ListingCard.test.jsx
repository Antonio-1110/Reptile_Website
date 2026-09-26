import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import ListingCard from './ListingCard';

const animal = {
  id: 12, title: 'Pastel Pied Ball Python', image: 'https://example.com/p.jpg', sex: '0.1', genes: ['Pastel', 'Pied'],
  location: 'taipei', price: '9000.00', seller: 'Apex Exotics', sellerTag: 'apex_exotics',
};

describe('ListingCard', () => {
  it('shows what a buyer scans for and links to the listing', () => {
    render(<ListingCard animal={animal} />);
    expect(screen.getByRole('img', { name: animal.title })).toHaveAttribute('src', animal.image);
    expect(screen.getByText('Pastel')).toBeInTheDocument();
    expect(screen.getByText('Pied')).toBeInTheDocument();
    expect(screen.getByText('$9000.00')).toBeInTheDocument();
    expect(screen.getByText(/Taipei City/)).toBeInTheDocument();
    expect(screen.getAllByRole('link').some((link) => link.getAttribute('href') === '/posts/12')).toBe(true);
    expect(screen.getByRole('link', { name: 'apex_exotics' })).toBeInTheDocument();
  });
});
