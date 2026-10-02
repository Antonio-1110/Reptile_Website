// Runs before every test file: DOM matchers (toBeInTheDocument, …), the real translations in English,
// and a clean slate between tests.
import '@testing-library/jest-dom/vitest';
import { cleanup } from '@testing-library/react';
import { afterEach, beforeEach, vi } from 'vitest';
import i18n from '../i18n';
import { setFeatures } from '../hooks/useFeature';

await i18n.changeLanguage('en');

// Components see every switchable feature on unless a test switches it off (setFeatures).
beforeEach(() => setFeatures({ auctions: true }));

afterEach(() => {
  cleanup();
  localStorage.clear();
  vi.restoreAllMocks();
});
