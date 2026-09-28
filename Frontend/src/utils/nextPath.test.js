import { describe, expect, it } from 'vitest';
import { safeNextPath } from './nextPath';

describe('safeNextPath', () => {
  it('keeps a same-site path', () => {
    expect(safeNextPath('?next=%2Forders%3Ftab%3D1')).toBe('/orders?tab=1');
  });

  it('falls back for missing or off-site targets', () => {
    expect(safeNextPath('')).toBe('/marketplace');
    expect(safeNextPath('?next=https://evil.example')).toBe('/marketplace');
    expect(safeNextPath('?next=//evil.example')).toBe('/marketplace');
  });
});
