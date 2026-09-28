import '../SignInPage.css';
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useLocation, useNavigate } from 'react-router';
import { getCurrentProfile, updateCurrentProfile } from '../../api/listingsApi';
import { errorText, toErrorState } from '../../utils/errorState';
import { safeNextPath } from '../../utils/nextPath';

// Shown once, right after Google sign-in creates an account. That account's username was made from the
// email address, which often gives away the person's real name, and usernames are public.
export default function ChooseUsernamePage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { search } = useLocation();
  const next = safeNextPath(search);
  const [current, setCurrent] = useState(null);
  const [username, setUsername] = useState('');
  const [loadError, setLoadError] = useState(null);
  const [fieldError, setFieldError] = useState('');
  const [formError, setFormError] = useState(null);
  const [saving, setSaving] = useState(false);

  const load = () => {
    setLoadError(null);
    getCurrentProfile()
      .then((profile) => {
        setCurrent(profile.username);
        setUsername(profile.username);
      })
      .catch((error) => setLoadError(toErrorState(error, 'chooseUsername.loadError')));
  };

  useEffect(load, []);

  const handleSubmit = async (event) => {
    event.preventDefault();
    const chosen = username.trim();
    if (chosen === current) {
      navigate(next, { replace: true });
      return;
    }
    setSaving(true);
    setFieldError('');
    setFormError(null);
    try {
      await updateCurrentProfile({ username: chosen });
      navigate(next, { replace: true });
    } catch (error) {
      setSaving(false);
      if (error.fields?.username) setFieldError(error.fields.username);
      else setFormError(toErrorState(error, 'auth.genericError'));
    }
  };

  return (
    <div className="authPage">
      <div className="authCard">
        <h1 className="authTitle">{t('chooseUsername.title')}</h1>
        <p className="authSubtitle">{t('chooseUsername.subtitle')}</p>
        {current === null ? (
          loadError ? (
            <>
              <p className="authFormError" role="alert">{errorText(t, loadError)}</p>
              <p className="authSwitch"><button type="button" onClick={load}>{t('listings.retry')}</button></p>
            </>
          ) : (
            <p className="authSubtitle" role="status">{t('auth.pleaseWait')}</p>
          )
        ) : (
          <form className="authForm" onSubmit={handleSubmit}>
            <label className="authField">
              <span>{t('auth.username')}</span>
              <input
                type="text"
                name="username"
                value={username}
                onChange={(event) => { setUsername(event.target.value); setFieldError(''); }}
                autoComplete="username"
                maxLength={150}
                aria-invalid={Boolean(fieldError)}
                aria-describedby="username-hint"
                required
              />
              {fieldError && <small className="authFieldError">{fieldError}</small>}
            </label>
            <p id="username-hint" className="authHint">{t('chooseUsername.hint')}</p>
            {formError && <p className="authFormError" role="alert">{errorText(t, formError)}</p>}
            <button type="submit" className="authSubmit" disabled={saving}>
              {saving ? t('auth.pleaseWait') : t('chooseUsername.continue')}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
