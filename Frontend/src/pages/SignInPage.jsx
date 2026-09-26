import './SignInPage.css';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { login, register } from '../api/authApi';

// Only allow same-site relative redirects, so ?next= can't send users off-site.
function getNextPath() {
  const next = new URLSearchParams(window.location.search).get('next') || '';
  return next.startsWith('/') && !next.startsWith('//') ? next : '/marketplace';
}

const emptyForm = { username: '', email: '', password: '', confirmPassword: '' };

// Errors for fields the form doesn't show (e.g. non_field_errors) would otherwise vanish, so they're
// collected into the form-level message instead.
function splitFieldErrors(fields) {
  const shown = {};
  const other = [];
  Object.entries(fields).forEach(([name, message]) => {
    if (name in emptyForm) shown[name] = message;
    else other.push(message);
  });
  if (other.length) shown.form = other.join(' ');
  return shown;
}

export default function SignInPage() {
  const { t } = useTranslation();
  const [mode, setMode] = useState(() => (
    new URLSearchParams(window.location.search).get('mode') === 'register' ? 'register' : 'signin'
  ));
  const [form, setForm] = useState(emptyForm);
  const [errors, setErrors] = useState({});
  const [submitting, setSubmitting] = useState(false);
  const isRegister = mode === 'register';
  const [hasNext] = useState(() => new URLSearchParams(window.location.search).has('next'));

  const switchMode = (nextMode) => {
    setMode(nextMode);
    setErrors({});
    setForm((current) => ({ ...current, password: '', confirmPassword: '' }));
  };

  const updateField = (field) => (event) => {
    setForm((current) => ({ ...current, [field]: event.target.value }));
    setErrors((current) => ({ ...current, [field]: undefined, form: undefined }));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (isRegister && form.password !== form.confirmPassword) {
      setErrors({ confirmPassword: t('auth.passwordsDontMatch') });
      return;
    }

    setSubmitting(true);
    setErrors({});
    try {
      if (isRegister) {
        await register({ username: form.username.trim(), email: form.email.trim(), password: form.password });
      } else {
        await login(form.username.trim(), form.password);
      }
      // A full load rather than navigate(), so every page and the header start from the new session.
      window.location.href = getNextPath();
    } catch (error) {
      setSubmitting(false);
      // register() signs in right after creating the account; if only that step failed, the account
      // exists and retrying "Create account" would just report the username as taken.
      if (error.accountCreated) {
        setMode('signin');
        setForm((current) => ({ ...current, password: '', confirmPassword: '' }));
        setErrors({ form: t('auth.registeredButLoginFailed') });
        return;
      }
      const hasFieldErrors = error.fields && Object.keys(error.fields).length > 0;
      setErrors(hasFieldErrors
        ? splitFieldErrors(error.fields)
        : { form: error.status === 401 ? t('auth.invalidCredentials') : (error.message || t('auth.genericError')) });
    }
  };

  const field = (name, label, type = 'text', autoComplete = undefined) => (
    <label className="authField">
      <span>{label}</span>
      <input
        type={type}
        name={name}
        value={form[name]}
        onChange={updateField(name)}
        autoComplete={autoComplete}
        aria-invalid={Boolean(errors[name])}
        required
      />
      {errors[name] && <small className="authFieldError">{errors[name]}</small>}
    </label>
  );

  return (
    <div className="authPage">
      <div className="authCard">
        <div className="authTabs" role="tablist">
          <button type="button" role="tab" aria-selected={!isRegister} className={!isRegister ? 'active' : ''} onClick={() => switchMode('signin')}>
            {t('auth.signIn')}
          </button>
          <button type="button" role="tab" aria-selected={isRegister} className={isRegister ? 'active' : ''} onClick={() => switchMode('register')}>
            {t('auth.createAccount')}
          </button>
        </div>

        <h1 className="authTitle">{isRegister ? t('auth.registerTitle') : t('auth.signInTitle')}</h1>
        <p className="authSubtitle">{isRegister ? t('auth.registerSubtitle') : t('auth.signInSubtitle')}</p>
        {hasNext && !isRegister && <p className="authNotice" role="status">{t('auth.signInToContinue')}</p>}

        <form className="authForm" onSubmit={handleSubmit}>
          {field('username', t('auth.username'), 'text', 'username')}
          {isRegister && field('email', t('auth.email'), 'email', 'email')}
          {field('password', t('auth.password'), 'password', isRegister ? 'new-password' : 'current-password')}
          {isRegister && field('confirmPassword', t('auth.confirmPassword'), 'password', 'new-password')}

          {errors.form && <p className="authFormError" role="alert">{errors.form}</p>}

          <button type="submit" className="authSubmit" disabled={submitting}>
            {submitting ? t('auth.pleaseWait') : (isRegister ? t('auth.createAccount') : t('auth.signIn'))}
          </button>
        </form>

        <p className="authSwitch">
          {isRegister ? t('auth.haveAccount') : t('auth.noAccount')}{' '}
          <button type="button" onClick={() => switchMode(isRegister ? 'signin' : 'register')}>
            {isRegister ? t('auth.signIn') : t('auth.createAccount')}
          </button>
        </p>
      </div>
    </div>
  );
}
