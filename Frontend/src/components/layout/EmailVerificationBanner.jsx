import './EmailVerificationBanner.css';
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { getMe, isLoggedIn, resendVerificationEmail } from '../../api/authApi';
import { errorText, toErrorState } from '../../utils/errorState';

// Reminds a signed-in user who hasn't opened the sign-up email yet why posting, contacting sellers and
// bidding are refused (the backend enforces it), and lets them ask for a new link.
export default function EmailVerificationBanner() {
  const { t } = useTranslation();
  const [unverified, setUnverified] = useState(false);
  const [sending, setSending] = useState(false);
  const [sent, setSent] = useState('');
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!isLoggedIn()) return undefined;
    let cancelled = false;
    // Not worth an error of its own: without the answer the banner simply stays hidden.
    getMe()
      .then((me) => { if (!cancelled) setUnverified(me.email_verified === false); })
      .catch(() => {});
    return () => { cancelled = true; };
  }, []);

  if (!unverified) return null;

  const resend = async () => {
    setSending(true);
    setError(null);
    try {
      setSent((await resendVerificationEmail()).detail);
    } catch (caught) {
      setError(toErrorState(caught, 'auth.genericError'));
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="emailVerificationBanner" role="region" aria-label={t('accountEmail.verifyTitle')}>
      <p>{t('accountEmail.bannerText')}</p>
      {sent ? (
        <p role="status" className="emailVerificationBannerStatus">{sent}</p>
      ) : (
        <button type="button" onClick={resend} disabled={sending}>
          {sending ? t('accountEmail.sending') : t('accountEmail.resend')}
        </button>
      )}
      {error && <p role="alert" className="emailVerificationBannerError">{errorText(t, error)}</p>}
    </div>
  );
}
