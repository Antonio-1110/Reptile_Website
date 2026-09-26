// Runs before every test file: DOM matchers (toBeInTheDocument, …), the real translations in English,
// and a clean slate between tests.
import '@testing-library/jest-dom/vitest';
import { cleanup } from '@testing-library/react';
import { afterEach, vi } from 'vitest';
import i18n from '../i18n';

await i18n.changeLanguage('en');

afterEach(() => {
  cleanup();
  localStorage.clear();
  vi.restoreAllMocks();
});
