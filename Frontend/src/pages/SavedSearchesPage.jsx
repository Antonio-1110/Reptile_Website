import './SavedSearchesPage.css';
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { deleteSavedSearch, getSavedSearches, isLoggedIn } from '../api/listingsApi';
import { formatDateTime } from '../utils/auctionFormat';
import { errorText, toErrorState } from '../utils/errorState';
import { Link } from 'react-router';

// How many filters a saved query has besides the search text (e.g. "sex=1.0&price_max=9000" → 2).
function filterCount(query) {
  return [...new URLSearchParams(query).keys()].filter((key) => key !== 'search').length;
}

// The searches the user saved from the marketplace. Each one is emailed about when new listings match
// it (the backend's send_search_alerts job); here they can see and delete them.
export default function SavedSearchesPage() {
  const { t, i18n } = useTranslation();
  const [searches, setSearches] = useState(null);
  const [error, setError] = useState(null);
  const [deletingId, setDeletingId] = useState(null);

  useEffect(() => {
    if (!isLoggedIn()) return;
    getSavedSearches().then(setSearches).catch((loadError) => setError(toErrorState(loadError, 'savedSearches.loadError')));
  }, []);

  if (!isLoggedIn()) {
    return (
      <div className="saved-searches-page saved-searches-page--center">
        <h1>{t('savedSearches.signedOutTitle')}</h1>
        <Link to="/signin?next=/saved-searches">{t('auth.signIn')}</Link>
      </div>
    );
  }

  const remove = async (search) => {
    setDeletingId(search.id);
    setError(null);
    try {
      await deleteSavedSearch(search.id);
      setSearches((current) => current.filter((item) => item.id !== search.id));
    } catch (deleteError) {
      setError(toErrorState(deleteError, 'savedSearches.deleteError'));
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <div className="saved-searches-page">
      <div className="saved-searches-inner">
        <h1>{t('savedSearches.title')}</h1>
        <p className="saved-searches-subtitle">{t('savedSearches.subtitle')}</p>
        {error && <p role="alert" className="saved-searches-error">{errorText(t, error)}</p>}
        {searches === null && !error && <p className="saved-searches-status">{t('savedSearches.loading')}</p>}
        {searches && searches.length === 0 && (
          <div className="saved-searches-empty">
            <p>{t('savedSearches.empty')}</p>
            <Link to="/marketplace">{t('navigation.browseMarketplace')}</Link>
          </div>
        )}
        {searches && searches.length > 0 && (
          <ul className="saved-searches-list">
            {searches.map((search) => {
              const filters = filterCount(search.query);
              return (
                <li key={search.id}>
                  <div>
                    <h2>🔔 {search.name}</h2>
                    <p>
                      {filters > 0 ? t('savedSearches.filters', { count: filters }) : t('savedSearches.noFilters')}
                      {' · '}
                      {t('savedSearches.since', { date: formatDateTime(search.createdAt, i18n.resolvedLanguage) })}
                    </p>
                  </div>
                  <button type="button" disabled={deletingId === search.id} onClick={() => remove(search)}>
                    {deletingId === search.id ? t('auctions.pleaseWait') : t('savedSearches.delete')}
                  </button>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </div>
  );
}
