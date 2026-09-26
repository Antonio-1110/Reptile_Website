import './FavoriteButton.css';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useLocation, useNavigate } from 'react-router';
import { isLoggedIn, setFavorite } from '../../api/listingsApi';

// The heart that saves a listing. Signed-out visitors are sent to sign in and come back. The change
// shows at once and is undone if the request fails.
export default function FavoriteButton({ listingId, category = 'live_animal', initial = false, className = '', onChange }) {
  const { t } = useTranslation();
  const location = useLocation();
  const navigate = useNavigate();
  const [saved, setSaved] = useState(initial);
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState(false);

  const toggle = async () => {
    if (!isLoggedIn()) {
      navigate(`/signin?next=${encodeURIComponent(location.pathname + location.search)}`);
      return;
    }
    const want = !saved;
    setSaved(want);
    setBusy(true);
    setFailed(false);
    try {
      const result = await setFavorite(listingId, category, want);
      setSaved(result);
      onChange?.(result);
    } catch {
      setSaved(!want);
      setFailed(true);
    } finally {
      setBusy(false);
    }
  };

  const label = saved ? t('favorites.unsave') : t('favorites.save');
  return (
    <button
      type="button"
      className={`favorite-button${saved ? ' is-saved' : ''}${className ? ` ${className}` : ''}`}
      aria-pressed={saved}
      aria-label={failed ? `${label} — ${t('favorites.error')}` : label}
      title={failed ? t('favorites.error') : label}
      disabled={busy}
      onClick={toggle}
    >
      <span aria-hidden="true">{saved ? '♥' : '♡'}</span>
    </button>
  );
}
