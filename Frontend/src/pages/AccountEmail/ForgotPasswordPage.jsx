import '../SignInPage.css';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router';
import { requestPasswordReset } from '../../api/authApi';
import { errorText, toErrorState } from '../../utils/errorState';

export default function ForgotPasswordPage() {
  const { t } = useTranslation();
  const [email, setEmail] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [sent, setSent] = useState('');
  const [error, setError] = useState(null);

  const handleSubmit = async (event) => {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const response = await requestPasswordReset(email.trim());
      setSent(response.detail);
    } catch (caught) {
      setError(toErrorState(caught, 'auth.genericError'));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="authPage">
      <div className="authCard">
        <h1 className="authTitle">{t('accountEmail.forgotTitle')}</h1>
        <p className="authSubtitle">{t('accountEmail.forgotSubtitle')}</p>
        {sent ? (
          <p className="authNotice authNoticeStandalone" role="status">{sent}</p>
        ) : (
          <form className="authForm" onSubmit={handleSubmit}>
            <label className="authField">
              <span>{t('auth.email')}</span>
              <input
                type="email"
                name="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                autoComplete="email"
                required
              />
            </label>
            {error && <p className="authFormError" role="alert">{errorText(t, error)}</p>}
            <button type="submit" className="authSubmit" disabled={submitting}>
              {submitting ? t('auth.pleaseWait') : t('accountEmail.sendLink')}
            </button>
          </form>
        )}
        <p className="authSwitch"><Link to="/signin">{t('accountEmail.backToSignIn')}</Link></p>
      </div>
    </div>
  );
}
