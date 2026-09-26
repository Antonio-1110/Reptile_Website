import './SellerProfilePage.css';
import { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import BackLink from '../components/ui/BackLink';
import ListingCard from '../components/listings/ListingCard';
import ListingGrid from '../components/listings/ListingGrid';
import { getListingsPage, getSellerProfile } from '../api/listingsApi';
import SellerReviews from './SellerReviews';
import { intlLocale } from '../utils/auctionFormat';
import { errorText, toErrorState } from '../utils/errorState';
import { Link } from 'react-router';

// A seller's public page: who they are, their badges and rating, and their listings. No contact
// details: buyers reach a seller through a listing's "Contact seller".
export default function SellerProfilePage({ sellerId }) {
  const { t, i18n } = useTranslation();
  const [profile, setProfile] = useState(null); // null loading, false not found
  const [profileError, setProfileError] = useState(null);
  const [feed, setFeed] = useState({ listings: [], nextPage: 1, loading: true, error: null });

  const loadListings = useCallback((page) => {
    setFeed((current) => ({ ...current, loading: true, error: null }));
    getListingsPage({ seller: sellerId, page })
      .then(({ results, hasMore }) => setFeed((current) => ({
        listings: page === 1 ? results : [...current.listings, ...results],
        nextPage: hasMore ? page + 1 : null,
        loading: false,
        error: null,
      })))
      .catch((error) => setFeed((current) => ({ ...current, loading: false, error: toErrorState(error, 'listings.loadError') })));
  }, [sellerId]);

  const loadProfile = useCallback(() => {
    getSellerProfile(sellerId)
      .then(setProfile)
      .catch((error) => (error.status === 404 ? setProfile(false) : setProfileError(toErrorState(error, 'sellerProfile.loadError'))));
  }, [sellerId]);

  useEffect(() => {
    loadProfile();
    loadListings(1);
  }, [loadProfile, loadListings]);

  if (profileError) {
    return <div className="seller-page"><p role="alert" className="seller-page-error">{errorText(t, profileError)}</p></div>;
  }
  if (profile === null) return <div className="seller-page"><p className="seller-page-status">{t('sellerProfile.loading')}</p></div>;
  if (profile === false) {
    return (
      <div className="seller-page">
        <div className="seller-page-missing">
          <h1>{t('sellerProfile.notFound')}</h1>
          <Link to="/marketplace">{t('navigation.backToMarketplace')}</Link>
        </div>
      </div>
    );
  }

  const since = new Intl.DateTimeFormat(intlLocale(i18n.resolvedLanguage), { year: 'numeric', month: 'long' }).format(profile.memberSince);
  return (
    <div className="seller-page">
      <div className="seller-page-inner">
        <BackLink to="/marketplace">{t('navigation.backToMarketplace')}</BackLink>
        <section className="seller-card">
          <div className="seller-avatar" aria-hidden="true">{(profile.displayName || profile.username).slice(0, 1).toUpperCase()}</div>
          <div className="seller-card-body">
            <h1>{profile.displayName}</h1>
            <p className="seller-username">@{profile.username}</p>
            <div className="seller-badges">
              {profile.verified && <span className="seller-badge seller-badge--verified">✓ {t('sellerProfile.verified')}</span>}
              <span className="seller-badge">{t(profile.isCommercial ? 'sellerProfile.commercial' : 'sellerProfile.hobbyist')}</span>
              <span className="seller-badge">
                {profile.totalReviews > 0
                  ? t('sellerProfile.rating', { rating: profile.rating.toFixed(1), count: profile.totalReviews })
                  : t('sellerProfile.noReviews')}
              </span>
            </div>
            <p className="seller-since">{t('sellerProfile.memberSince', { date: since })}</p>
            {profile.bio && <p className="seller-bio">{profile.bio}</p>}
          </div>
        </section>

        {/* Refreshing the profile after a review updates the rating badge above. */}
        <SellerReviews profile={profile} onRatingChanged={loadProfile} />

        <h2 className="seller-listings-heading">{t('sellerProfile.listings', { count: profile.liveAnimalCount })}</h2>
        {profile.equipmentCount > 0 && <p className="seller-page-status">{t('sellerProfile.equipmentCount', { count: profile.equipmentCount })}</p>}
        {feed.error && (
          <p role="alert" className="seller-page-error">
            {errorText(t, feed.error)}{' '}
            <button type="button" className="seller-page-retry" onClick={() => loadListings(feed.nextPage || 1)}>{t('listings.retry')}</button>
          </p>
        )}
        {feed.loading && feed.listings.length === 0 && <p className="seller-page-status">{t('listings.loading')}</p>}
        {!feed.loading && !feed.error && feed.listings.length === 0 && <p className="seller-page-empty">{t('sellerProfile.noListings')}</p>}
        {feed.listings.length > 0 && (
          <ListingGrid>
            {feed.listings.map((listing) => <ListingCard key={listing.id} animal={listing} />)}
          </ListingGrid>
        )}
        {feed.nextPage && feed.listings.length > 0 && !feed.error && (
          <button type="button" className="seller-page-more" disabled={feed.loading} onClick={() => loadListings(feed.nextPage)}>
            {feed.loading ? t('listings.loadingMore') : t('sellerProfile.showMore')}
          </button>
        )}
      </div>
    </div>
  );
}
