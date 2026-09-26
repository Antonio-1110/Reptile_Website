import { describe, expect, it } from 'vitest';
import i18n from '../i18n';
import { matchSpecies, normalizeSpeciesName } from './species';

const t = i18n.t.bind(i18n);
const SPECIES = [
  { id: 1, name: 'Ball Pythons', aliases: ['Royal Python'] },
  { id: 2, name: 'Blue-tongued Skinks', aliases: ['藍舌蜥'] },
];

describe('normalizeSpeciesName', () => {
  it('ignores case, spacing and punctuation but keeps Chinese characters', () => {
    expect(normalizeSpeciesName('  Blue-Tongued  skinks ')).toBe('bluetonguedskinks');
    expect(normalizeSpeciesName('藍舌 蜥')).toBe('藍舌蜥');
  });
});

describe('matchSpecies', () => {
  it('suggests species by label, stored name or alias', () => {
    expect(matchSpecies(t, SPECIES, 'python').matches.map((s) => s.id)).toEqual([1]);
    expect(matchSpecies(t, SPECIES, 'royal').matches.map((s) => s.id)).toEqual([1]);
    expect(matchSpecies(t, SPECIES, '藍舌').matches.map((s) => s.id)).toEqual([2]);
  });

  it('finds the exact match, or none for a name that needs review', () => {
    expect(matchSpecies(t, SPECIES, 'royal python').exact?.id).toBe(1);
    expect(matchSpecies(t, SPECIES, 'blue tongued skinks').exact?.id).toBe(2);
    expect(matchSpecies(t, SPECIES, 'Blue').exact).toBeNull();
    expect(matchSpecies(t, SPECIES, 'Frilled Lizard')).toEqual({ matches: [], exact: null });
    expect(matchSpecies(t, SPECIES, '  ')).toEqual({ matches: [], exact: null });
  });
});
