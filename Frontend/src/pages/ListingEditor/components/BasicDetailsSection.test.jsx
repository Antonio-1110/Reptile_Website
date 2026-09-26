import { fireEvent, render, screen } from '@testing-library/react';
import { useState } from 'react';
import { describe, expect, it, vi } from 'vitest';
import BasicDetailsSection from './BasicDetailsSection';

const SPECIES = [
  { id: 1, name: 'Ball Pythons', aliases: ['Royal Python'] },
  { id: 2, name: 'Blood Pythons', aliases: [] },
  { id: 3, name: 'Carpet Pythons', aliases: [] },
];

// The editor keeps the species in its form state; this stands in for it.
function Editor({ onSpeciesChange = () => {} }) {
  const [formData, setFormData] = useState({
    title: '', description: '', price: '', category: 'live_animal', species: '', speciesId: null,
  });
  return (
    <form onSubmit={(event) => event.preventDefault()}>
      <BasicDetailsSection
        formData={formData}
        onChange={() => {}}
        speciesList={SPECIES}
        onSpeciesChange={(species, speciesId) => {
          onSpeciesChange(species, speciesId);
          setFormData((current) => ({ ...current, species, speciesId }));
        }}
      />
    </form>
  );
}

const input = () => screen.getByRole('combobox', { name: 'Species' });
const press = (key) => fireEvent.keyDown(input(), { key });
const highlighted = () => screen.getByRole('option', { selected: true });

describe('BasicDetailsSection species picker', () => {
  it('moves through the options with the arrow keys, wrapping around, and picks one with Enter', () => {
    const onSpeciesChange = vi.fn();
    render(<Editor onSpeciesChange={onSpeciesChange} />);
    fireEvent.change(input(), { target: { value: 'python' } });
    expect(screen.getAllByRole('option').map((option) => option.textContent)).toEqual([
      'Ball Pythons', 'Blood Pythons', 'Carpet Pythons', 'Use “python” (we\'ll review it)',
    ]);
    expect(screen.queryByRole('option', { selected: true })).toBeNull();

    press('ArrowDown');
    expect(highlighted()).toHaveTextContent('Ball Pythons');
    expect(input()).toHaveAttribute('aria-activedescendant', highlighted().id);
    press('ArrowDown');
    expect(highlighted()).toHaveTextContent('Blood Pythons');
    press('ArrowUp');
    press('ArrowUp');
    expect(highlighted()).toHaveTextContent('we\'ll review it'); // wrapped to the last option

    press('ArrowDown');
    press('ArrowDown');
    expect(highlighted()).toHaveTextContent('Blood Pythons');
    press('Enter');
    expect(onSpeciesChange).toHaveBeenLastCalledWith('Blood Pythons', 2);
    expect(screen.queryByRole('listbox')).toBeNull();
    expect(input()).toHaveValue('Blood Pythons');
    expect(input()).toHaveAttribute('aria-expanded', 'false');
  });

  it('keeps a typed name for review when that option is chosen, and Escape closes the menu', () => {
    const onSpeciesChange = vi.fn();
    render(<Editor onSpeciesChange={onSpeciesChange} />);
    fireEvent.change(input(), { target: { value: 'Frilled Lizard' } });
    press('ArrowDown');
    expect(highlighted()).toHaveTextContent('Use “Frilled Lizard”');
    press('Enter');
    expect(onSpeciesChange).toHaveBeenLastCalledWith('Frilled Lizard', null);
    expect(screen.queryByRole('listbox')).toBeNull();
    expect(screen.getByText(/isn't in our species list yet/)).toBeInTheDocument();

    press('ArrowDown'); // reopens the menu
    expect(screen.getByRole('listbox')).toBeInTheDocument();
    press('Escape');
    expect(screen.queryByRole('listbox')).toBeNull();
  });

  it('leaves Enter to the form when no option is highlighted', () => {
    const onSpeciesChange = vi.fn();
    render(<Editor onSpeciesChange={onSpeciesChange} />);
    fireEvent.change(input(), { target: { value: 'python' } });
    onSpeciesChange.mockClear();
    const event = fireEvent.keyDown(input(), { key: 'Enter' });
    expect(event).toBe(true); // not prevented
    expect(onSpeciesChange).not.toHaveBeenCalled();
  });
});
