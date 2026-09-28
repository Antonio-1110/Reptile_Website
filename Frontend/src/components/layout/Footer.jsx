import './Footer.css';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router';

export default function Footer() {
  const { t } = useTranslation();
  return (
    <footer className="site-footer">
      <span>{t('legal.copyright', { year: new Date().getFullYear() })}</span>
      <nav aria-label={t('legal.footerNav')}>
        <Link to="/privacy">{t('legal.privacyLink')}</Link>
        <Link to="/terms">{t('legal.termsLink')}</Link>
      </nav>
    </footer>
  );
}
