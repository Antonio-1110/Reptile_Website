import './GoogleSignInButton.css';
import { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';

// The OAuth client ID from Google Cloud Console. Without one the button isn't shown at all.
const CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID;
const SCRIPT_URL = 'https://accounts.google.com/gsi/client';
let scriptPromise;

// Google Identity Services is only loaded on the sign-in page, and only once.
function loadGoogleScript() {
  if (window.google?.accounts?.id) return Promise.resolve(window.google);
  scriptPromise ??= new Promise((resolve, reject) => {
    const script = document.createElement('script');
    script.src = SCRIPT_URL;
    script.async = true;
    script.onload = () => resolve(window.google);
    script.onerror = () => {
      scriptPromise = undefined;
      script.remove();
      reject(new Error('Google sign-in script failed to load'));
    };
    document.head.appendChild(script);
  });
  return scriptPromise;
}

// Google draws the button itself (its branding rules require it), in the page's language. The ID
// token it hands back goes to onCredential, which exchanges it for our own sign-in tokens.
export default function GoogleSignInButton({ onCredential, disabled = false }) {
  const { t, i18n } = useTranslation();
  const container = useRef(null);
  const onCredentialRef = useRef(onCredential);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    onCredentialRef.current = onCredential;
  }, [onCredential]);

  useEffect(() => {
    if (!CLIENT_ID) return undefined;
    let cancelled = false;
    loadGoogleScript()
      .then((google) => {
        if (cancelled || !container.current) return;
        google.accounts.id.initialize({
          client_id: CLIENT_ID,
          callback: (response) => onCredentialRef.current(response.credential),
        });
        container.current.replaceChildren();
        google.accounts.id.renderButton(container.current, {
          theme: 'outline',
          size: 'large',
          shape: 'pill',
          text: 'continue_with',
          width: Math.max(200, Math.min(container.current.offsetWidth || 320, 400)),
          locale: i18n.language.startsWith('zh') ? 'zh-TW' : 'en',
        });
      })
      .catch(() => {
        if (!cancelled) setFailed(true);
      });
    return () => {
      cancelled = true;
    };
  }, [i18n.language]);

  if (!CLIENT_ID) return null;
  return (
    <div className="googleSignIn">
      <p className="googleSignInDivider"><span>{t('signInOptions.or')}</span></p>
      <div ref={container} className={`googleSignInButton${disabled ? ' isDisabled' : ''}`} aria-busy={disabled} />
      {failed && <p className="authFormError" role="alert">{t('signInOptions.googleUnavailable')}</p>}
    </div>
  );
}
