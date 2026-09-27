import '../SignInPage.css';
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link, useSearchParams } from 'react-router';
import { verifyEmail } from '../../api/authApi';
import { errorText, toErrorState } from '../../utils/errorState';

// Opened from the sign-up email: /verify-email?uid=…&token=… Works signed in or out (the link may be
// opened on another device); the backend treats opening it twice as success.
export default function VerifyEmailPage() {
  const { t } = useTranslation();
  const [params] = useSearchParams();
  const uid = params.get('uid');
  const token = params.get('token');
  const [result, setResult] = useState(() => (
    uid && token ? { status: 'loading' } : { status: 'error', error: { key: 'accountEmail.incompleteLink' } }
  ));

  useEffect(() => {
    if (!uid || !token) return undefined;
    let cancelled = false;
    verifyEmail({ uid, token })
      .then((response) => { if (!cancelled) setResult({ status: 'done', message: response.detail }); })
      .catch((error) => { if (!cancelled) setResult({ status: 'error', error: toErrorState(error, 'auth.genericError') }); });
    return () => { cancelled = true; };
  }, [uid, token]);

  return (
    <div className="authPage">
      <div className="authCard">
        <h1 className="authTitle authTitleSpaced">{t('accountEmail.verifyTitle')}</h1>
        {result.status === 'loading' && <p className="authSubtitle" role="status">{t('accountEmail.verifying')}</p>}
        {result.status === 'done' && <p className="authNotice authNoticeStandalone" role="status">{result.message}</p>}
        {result.status === 'error' && <p className="authFormError" role="alert">{errorText(t, result.error)}</p>}
        <p className="authSwitch"><Link to="/marketplace">{t('accountEmail.goToMarketplace')}</Link></p>
      </div>
    </div>
  );
}
