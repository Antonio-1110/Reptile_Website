import '../SignInPage.css';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link, useSearchParams } from 'react-router';
import { resetPassword } from '../../api/authApi';
import { errorText, toErrorState } from '../../utils/errorState';

// Opened from the password-reset email: /reset-password?uid=…&token=…
export default function ResetPasswordPage() {
  const { t } = useTranslation();
  const [params] = useSearchParams();
  const uid = params.get('uid');
  const token = params.get('token');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState('');
  const [fieldError, setFieldError] = useState('');
  const [error, setError] = useState(null);

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (password !== confirmPassword) {
      setFieldError(t('auth.passwordsDontMatch'));
      return;
    }
    setSubmitting(true);
    setFieldError('');
    setError(null);
    try {
      const response = await resetPassword({ uid, token, password });
      setDone(response.detail);
    } catch (caught) {
      if (caught.fields?.password) setFieldError(caught.fields.password);
      else setError(toErrorState(caught, 'auth.genericError'));
    } finally {
      setSubmitting(false);
    }
  };

  let body;
  if (!uid || !token) {
    body = <p className="authFormError" role="alert">{t('accountEmail.incompleteLink')}</p>;
  } else if (done) {
    body = <p className="authNotice authNoticeStandalone" role="status">{done}</p>;
  } else {
    body = (
      <form className="authForm" onSubmit={handleSubmit}>
        <label className="authField">
          <span>{t('accountEmail.newPassword')}</span>
          <input
            type="password"
            name="password"
            value={password}
            onChange={(event) => { setPassword(event.target.value); setFieldError(''); }}
            autoComplete="new-password"
            aria-invalid={Boolean(fieldError)}
            required
          />
          {fieldError && <small className="authFieldError">{fieldError}</small>}
        </label>
        <label className="authField">
          <span>{t('auth.confirmPassword')}</span>
          <input
            type="password"
            name="confirmPassword"
            value={confirmPassword}
            onChange={(event) => { setConfirmPassword(event.target.value); setFieldError(''); }}
            autoComplete="new-password"
            required
          />
        </label>
        {error && (
          <p className="authFormError" role="alert">
            {errorText(t, error)} <Link to="/forgot-password">{t('accountEmail.askForNewLink')}</Link>
          </p>
        )}
        <button type="submit" className="authSubmit" disabled={submitting}>
          {submitting ? t('auth.pleaseWait') : t('accountEmail.savePassword')}
        </button>
      </form>
    );
  }

  return (
    <div className="authPage">
      <div className="authCard">
        <h1 className="authTitle authTitleSpaced">{t('accountEmail.resetTitle')}</h1>
        {body}
        <p className="authSwitch"><Link to="/signin">{done ? t('auth.signIn') : t('accountEmail.backToSignIn')}</Link></p>
      </div>
    </div>
  );
}
