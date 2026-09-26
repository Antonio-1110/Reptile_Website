import './SavedListingsPage.css';
import { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import ListingCard from '../components/listings/ListingCard';
import ListingGrid from '../components/listings/ListingGrid';
import { getFavoritesPage, isLoggedIn } from '../api/listingsApi';
import { errorText, toErrorState } from '../utils/errorState';
import { Link } from 'react-router';

// The animals the user saved with the heart, most recently saved first. Unsaving one here leaves it
// on the page (with an empty heart) until the next visit, so it can be saved again straight away.
export default function SavedListingsPage() {
  const { t } = useTranslation();
  const [feed, setFeed] = useState({ listings: null, count: 0, nextPage: 1, loading: true, error: null });

  const load = useCallback((page) => {
    setFeed((current) => ({ ...current, loading: true, error: null }));
    getFavoritesPage(page)
      .then(({ results, count, hasMore }) => setFeed((current) => ({
        listings: page === 1 ? results : [...(current.listings || []), ...results],
        count,
        nextPage: hasMore ? page + 1 : null,
        loading: false,
        error: null,
      })))
      .catch((error) => setFeed((current) => ({ ...current, loading: false, error: toErrorState(error, 'favorites.loadError') })));
  }, []);

  useEffect(() => {
    if (isLoggedIn()) load(1);
  }, [load]);

  if (!isLoggedIn()) {
    return (
      <div className="saved-page saved-page--center">
        <h1>{t('favorites.signedOutTitle')}</h1>
        <Link to="/signin?next=/saved">{t('auth.signIn')}</Link>
      </div>
    );
  }

  const { listings } = feed;
  return (
    <div className="saved-page">
      <div className="saved-page-inner">
        <h1>{t('favorites.title')}</h1>
        <p className="saved-page-subtitle">{t('favorites.subtitle')}</p>
        {feed.error && (
          <p role="alert" className="saved-page-error">
            {errorText(t, feed.error)}{' '}
            <button type="button" className="saved-page-retry" onClick={() => load(listings ? feed.nextPage || 1 : 1)}>{t('listings.retry')}</button>
          </p>
        )}
        {listings === null && feed.loading && <p className="saved-page-status">{t('listings.loading')}</p>}
        {listings && listings.length === 0 && (
          <div className="saved-page-empty">
            <p>{t('favorites.empty')}</p>
            <Link to="/marketplace">{t('navigation.browseMarketplace')}</Link>
          </div>
        )}
        {listings && listings.length > 0 && (
          <ListingGrid>
            {listings.map((listing) => <ListingCard key={listing.id} animal={listing} />)}
          </ListingGrid>
        )}
        {listings && feed.nextPage && !feed.error && (
          <button type="button" className="saved-page-more" disabled={feed.loading} onClick={() => load(feed.nextPage)}>
            {feed.loading ? t('listings.loadingMore') : t('favorites.showMore')}
          </button>
        )}
      </div>
    </div>
  );
}
