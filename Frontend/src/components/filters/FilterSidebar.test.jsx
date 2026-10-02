import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import FilterSidebar from './FilterSidebar';
import { countActiveFilters } from './activeFilters';

const noFilters = {
  minPrice: '', maxPrice: '', minSize: '', maxSize: '', minPostedDays: '', maxPostedDays: '', sex: [],
  locations: [], includeLocations: true, lifeStages: [], minAgeYears: '', maxAgeYears: '',
  minWeight: '', maxWeight: '', diets: [], shippingMethods: [], equipmentTypes: [], conditions: [],
};

const renderSidebar = (filters = noFilters, category = 'live_animal') => render(
  <FilterSidebar category={category} onCategoryChange={() => {}} filters={filters} setFilters={() => {}} />,
);

describe('FilterSidebar folding', () => {
  it('starts folded, with the category switch still shown', () => {
    renderSidebar();
    const toggle = screen.getByRole('button', { name: /Show filters/ });
    expect(toggle).toHaveAttribute('aria-expanded', 'false');
    expect(screen.getByRole('radio', { name: 'Equipment' })).toBeInTheDocument();
    expect(document.getElementById(toggle.getAttribute('aria-controls'))).toBeInTheDocument();
  });

  it('opens from the top and folds again from the bottom', () => {
    renderSidebar();
    fireEvent.click(screen.getByRole('button', { name: /Show filters/ }));
    const hideButtons = screen.getAllByRole('button', { name: /Hide filters/ });
    expect(hideButtons).toHaveLength(2);
    hideButtons.forEach((button) => expect(button).toHaveAttribute('aria-expanded', 'true'));
    fireEvent.click(hideButtons[1]);
    expect(screen.getByRole('button', { name: /Show filters/ })).toHaveAttribute('aria-expanded', 'false');
  });

  it('shows how many filters are on while folded', () => {
    renderSidebar({ ...noFilters, sex: ['1.0'], minPrice: '100', maxPrice: '500' });
    expect(screen.getByRole('button', { name: /Show filters/ })).toHaveTextContent('2 active');
  });

  it('scrolls the panel back into view when folded from the bottom', () => {
    const scrollIntoView = vi.fn();
    Element.prototype.scrollIntoView = scrollIntoView;
    renderSidebar();
    fireEvent.click(screen.getByRole('button', { name: /Show filters/ }));
    fireEvent.click(screen.getAllByRole('button', { name: /Hide filters/ })[1]);
    expect(scrollIntoView).toHaveBeenCalled();
    delete Element.prototype.scrollIntoView;
  });
});

describe('countActiveFilters', () => {
  it('counts a range once and ignores the other category', () => {
    const filters = { ...noFilters, minWeight: '10', maxWeight: '20', equipmentTypes: ['heating'] };
    expect(countActiveFilters('live_animal', filters)).toBe(1);
    expect(countActiveFilters('equipment', filters)).toBe(1);
    expect(countActiveFilters('equipment', noFilters)).toBe(0);
  });
});
