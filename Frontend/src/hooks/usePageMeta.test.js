import { renderHook } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import i18n from '../i18n';
import usePageMeta, { shortDescription } from './usePageMeta';

describe('usePageMeta', () => {
  beforeEach(async () => {
    await i18n.changeLanguage('en');
    document.head.innerHTML = '<meta name="description" content="Site-wide description" />';
  });
  afterEach(() => i18n.changeLanguage('en'));

  const description = () => document.querySelector('meta[name="description"]').content;

  it('sets the page title and description, and restores the site-wide ones on leaving', () => {
    const { unmount } = renderHook(() => usePageMeta('Ball python', 'A calm   pastel\nmale.'));
    expect(document.title).toBe('Ball python | Reptilian');
    expect(description()).toBe('A calm pastel male.');
    unmount();
    expect(document.title).toBe(i18n.t('app.title'));
    expect(description()).toBe('Site-wide description');
  });

  it('keeps the site-wide title while the page has nothing to show yet', () => {
    document.title = 'Reptilian';
    renderHook(() => usePageMeta(undefined, undefined));
    expect(document.title).toBe('Reptilian');
    expect(description()).toBe('Site-wide description');
  });

  it('keeps the page title after a language switch', async () => {
    const { rerender } = renderHook(() => usePageMeta('Ball python'));
    await i18n.changeLanguage('zh');
    rerender();
    expect(document.title).toBe('Ball python｜Reptilian');
  });

  it('shortens long descriptions to what a search result shows', () => {
    const text = shortDescription('x'.repeat(300));
    expect(text).toHaveLength(160);
    expect(text.endsWith('…')).toBe(true);
  });
});
