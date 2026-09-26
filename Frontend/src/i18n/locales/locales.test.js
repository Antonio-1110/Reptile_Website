import { describe, expect, it } from 'vitest';
import { en, zh } from './index';

// Flatten to dotted keys, folding i18next plural forms (_one, _other…) into their base key, since
// Chinese only needs _other.
const keys = (object, prefix = '') => Object.entries(object).flatMap(([key, value]) => (
  typeof value === 'object'
    ? keys(value, `${prefix}${key}.`)
    : [`${prefix}${key}`.replace(/_(zero|one|two|few|many|other)$/, '')]
));

describe('translations', () => {
  it('has the same section files in both languages', () => {
    expect(Object.keys(zh).sort()).toEqual(Object.keys(en).sort());
  });

  it('translates every English key into Chinese', () => {
    const chinese = new Set(keys(zh));
    // An `_equipment` context variant may fall back to its base key (see useListingTranslation).
    const missing = keys(en).filter((key) => !chinese.has(key) && !chinese.has(key.replace(/_equipment$/, '')));
    expect(missing).toEqual([]);
  });

  it('has no Chinese keys that English lacks', () => {
    const english = new Set(keys(en));
    expect(keys(zh).filter((key) => !english.has(key))).toEqual([]);
  });
});
