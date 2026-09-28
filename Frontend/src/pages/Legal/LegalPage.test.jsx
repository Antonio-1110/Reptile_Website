import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { afterEach, describe, expect, it } from 'vitest';
import i18n from '../../i18n';
import { SUPPORT_EMAIL } from '../../constants/site';
import LegalPage from './LegalPage';

const renderPage = (doc) => render(<LegalPage doc={doc} />, { wrapper: MemoryRouter });

describe('LegalPage', () => {
  afterEach(() => i18n.changeLanguage('en'));

  it('shows the privacy policy with its sections and a way to reach us', () => {
    renderPage('privacy');

    expect(screen.getByRole('heading', { level: 1, name: 'Privacy policy' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { level: 2, name: 'Your rights' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: SUPPORT_EMAIL })).toHaveAttribute('href', `mailto:${SUPPORT_EMAIL}`);
  });

  it('shows the terms in Chinese', async () => {
    await i18n.changeLanguage('zh');
    renderPage('terms');

    expect(screen.getByRole('heading', { level: 1, name: '服務條款' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { level: 2, name: '禁止的行為' })).toBeInTheDocument();
  });
});
