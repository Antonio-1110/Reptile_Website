import '../SignInPage.css';
import './ChangePasswordPage.css';
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router';
import { changePassword, requestPasswordReset } from '../../api/authApi';
import { getCurrentProfile } from '../../api/listingsApi';
import PasswordRules from '../../components/ui/PasswordRules';
import { errorText, toErrorState } from '../../utils/errorState';

// Changing the password from account settings. The current password proves it's the owner and not
// someone at an unlocked device; accounts made with Google sign-in have none, so they (and anyone who
// forgot theirs) get an emailed link instead.
export default function ChangePasswordPage() {
  const { t } = useTranslation();
  const [profile, setProfile] = useState(null);
  const [loadError, setLoadError] = useState(null);
  const [currentPassword, setCurrentPassword] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [fieldErrors, setFieldErrors] = useState({});
  const [formError, setFormError] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState('');
  const [linkSent, setLinkSent] = useState(false);

  const load = () => {
    setLoadError(null);
    getCurrentProfile().then(setProfile).catch((error) => setLoadError(toErrorState(error, 'accountSecurity.loadError')));
  };

  useEffect(load, []);

  const clearErrors = () => {
    setFieldErrors({});
    setFormError(null);
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (password !== confirmPassword) {
      setFieldErrors({ confirmPassword: t('auth.passwordsDontMatch') });
      return;
    }
    setSubmitting(true);
    clearErrors();
    try {
      await changePassword({ currentPassword, password });
      setDone(t('accountSecurity.changed'));
    } catch (error) {
      const fields = {};
      if (error.fields?.current_password) fields.currentPassword = error.fields.current_password;
      if (error.fields?.password) fields.password = error.fields.password;
      setFieldErrors(fields);
      if (!Object.keys(fields).length) setFormError(toErrorState(error, 'auth.genericError'));
    } finally {
      setSubmitting(false);
    }
  };

  const sendLink = async () => {
    setSubmitting(true);
    clearErrors();
    try {
      await requestPasswordReset(profile.email);
      setLinkSent(true);
    } catch (error) {
      setFormError(toErrorState(error, 'auth.genericError'));
    } finally {
      setSubmitting(false);
    }
  };

  const errorFor = (field) => fieldErrors[field] && <small className="authFieldError">{fieldErrors[field]}</small>;

  let body;
  if (!profile) {
    body = loadError ? (
      <>
        <p className="authFormError" role="alert">{errorText(t, loadError)}</p>
        <p className="authSwitch"><button type="button" onClick={load}>{t('listings.retry')}</button></p>
      </>
    ) : (
      <p className="authSubtitle" role="status">{t('auth.pleaseWait')}</p>
    );
  } else if (done || linkSent) {
    body = (
      <p className="authNotice authNoticeStandalone" role="status">
        {done || t('accountSecurity.linkSent', { email: profile.email })}
      </p>
    );
  } else if (!profile.has_password) {
    body = (
      <div className="authForm">
        <p className="authSubtitle">{t('accountSecurity.noPasswordYet', { email: profile.email })}</p>
        {formError && <p className="authFormError" role="alert">{errorText(t, formError)}</p>}
        <button type="button" className="authSubmit" onClick={sendLink} disabled={submitting}>
          {submitting ? t('auth.pleaseWait') : t('accountSecurity.sendLink')}
        </button>
      </div>
    );
  } else {
    body = (
      <form className="authForm" onSubmit={handleSubmit}>
        <p className="authSubtitle">{t('accountSecurity.subtitle')}</p>
        <label className="authField">
          <span>{t('accountSecurity.currentPassword')}</span>
          <input
            type="password"
            name="currentPassword"
            value={currentPassword}
            onChange={(event) => { setCurrentPassword(event.target.value); clearErrors(); }}
            autoComplete="current-password"
            aria-invalid={Boolean(fieldErrors.currentPassword)}
            required
          />
          {errorFor('currentPassword')}
        </label>
        <p className="authForgot">
          <button type="button" className="changePasswordLinkButton" onClick={sendLink} disabled={submitting}>
            {t('accountSecurity.forgotCurrent')}
          </button>
        </p>
        <label className="authField">
          <span>{t('accountEmail.newPassword')}</span>
          <input
            type="password"
            name="password"
            value={password}
            onChange={(event) => { setPassword(event.target.value); clearErrors(); }}
            autoComplete="new-password"
            aria-invalid={Boolean(fieldErrors.password)}
            aria-describedby="password-rules"
            required
          />
          {errorFor('password')}
        </label>
        <PasswordRules id="password-rules" password={password} />
        <label className="authField">
          <span>{t('auth.confirmPassword')}</span>
          <input
            type="password"
            name="confirmPassword"
            value={confirmPassword}
            onChange={(event) => { setConfirmPassword(event.target.value); clearErrors(); }}
            autoComplete="new-password"
            aria-invalid={Boolean(fieldErrors.confirmPassword)}
            required
          />
          {errorFor('confirmPassword')}
        </label>
        {formError && <p className="authFormError" role="alert">{errorText(t, formError)}</p>}
        <button type="submit" className="authSubmit" disabled={submitting}>
          {submitting ? t('auth.pleaseWait') : t('accountSecurity.save')}
        </button>
      </form>
    );
  }

  return (
    <div className="authPage">
      <div className="authCard">
        <h1 className="authTitle authTitleSpaced">
          {profile && !profile.has_password ? t('accountSecurity.setTitle') : t('accountSecurity.title')}
        </h1>
        {body}
        <p className="authSwitch"><Link to="/settings">{t('accountSecurity.backToSettings')}</Link></p>
      </div>
    </div>
  );
}
