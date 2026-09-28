import './SellerProfilePage.css';
import { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import BackLink from '../components/ui/BackLink';
import usePageMeta from '../hooks/usePageMeta';
import ListingCard from '../components/listings/ListingCard';
import ListingGrid from '../components/listings/ListingGrid';
import { getListingsPage, getSellerProfile } from '../api/listingsApi';
import { SellerReviewForm, SellerReviewList } from './SellerReviews';
import { intlLocale } from '../utils/auctionFormat';
import { errorText, toErrorState } from '../utils/errorState';
import { Link, useLocation, useNavigate } from 'react-router';
import CategorySwitch from '../components/ui/CategorySwitch';
import { MARKETPLACE_CATEGORIES, readMarketplaceCategory } from '../utils/marketplaceSearch';

// A seller's public page: who they are, their badges and rating, and their listings. No contact
// details: buyers reach a seller through a listing's "Contact seller".
export default function SellerProfilePage({ sellerId }) {
  const { t, i18n } = useTranslation();
  const location = useLocation();
  const navigate = useNavigate();
  // In the URL (?category=equipment) so Back and shared links keep the tab.
  const category = readMarketplaceCategory(location.search);
  const [profile, setProfile] = useState(null); // null loading, false not found
  usePageMeta(profile?.displayName, profile?.bio);
  const [profileError, setProfileError] = useState(null);
  const [feed, setFeed] = useState({ listings: [], nextPage: 1, loading: true, error: null });
  const [reviewsVersion, setReviewsVersion] = useState(0);

  const loadListings = useCallback((page) => {
    setFeed((current) => ({ ...current, loading: true, error: null }));
    getListingsPage({ seller: sellerId, category, page })
      .then(({ results, hasMore }) => setFeed((current) => ({
        listings: page === 1 ? results : [...current.listings, ...results],
        nextPage: hasMore ? page + 1 : null,
        loading: false,
        error: null,
      })))
      .catch((error) => setFeed((current) => ({ ...current, loading: false, error: toErrorState(error, 'listings.loadError') })));
  }, [sellerId, category]);

  const loadProfile = useCallback(() => {
    getSellerProfile(sellerId)
      .then(setProfile)
      .catch((error) => (error.status === 404 ? setProfile(false) : setProfileError(toErrorState(error, 'sellerProfile.loadError'))));
  }, [sellerId]);

  useEffect(() => {
    loadProfile();
  }, [loadProfile]);

  useEffect(() => {
    // Clear the other category's cards so they don't flash under the new tab while it loads.
    setFeed({ listings: [], nextPage: 1, loading: true, error: null });
    loadListings(1);
  }, [loadListings]);

  const changeCategory = (value) => {
    const params = new URLSearchParams(location.search);
    if (value === 'live_animal') params.delete('category');
    else params.set('category', value);
    const query = params.toString();
    navigate(`${location.pathname}${query ? `?${query}` : ''}`, { replace: true });
  };

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
        {/* Profile and the "rate this seller" panel side by side, then listings beside the reviews, so a
            long review history doesn't push the listings down the page. */}
        <div className="seller-top">
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
          {/* Refreshing the profile after a review updates the rating badge; the list reloads too. */}
          <SellerReviewForm
            profile={profile}
            onChanged={() => {
              loadProfile();
              setReviewsVersion((version) => version + 1);
            }}
          />
        </div>

        <div className="seller-columns">
          <section className="seller-listings" aria-labelledby="seller-listings-heading">
            <h2 id="seller-listings-heading" className="seller-listings-heading">{t('sellerProfile.listingsHeading')}</h2>
            <CategorySwitch
              className="seller-category"
              labelClassName="seller-category-label"
              label={t('sellerProfile.categoryLabel')}
              options={MARKETPLACE_CATEGORIES.map((value) => ({
                value,
                label: t(`sellerProfile.categoryTabs.${value}`, { count: value === 'equipment' ? profile.equipmentCount : profile.liveAnimalCount }),
              }))}
              value={category}
              onChange={changeCategory}
            />
            {feed.error && (
              <p role="alert" className="seller-page-error">
                {errorText(t, feed.error)}{' '}
                <button type="button" className="seller-page-retry" onClick={() => loadListings(feed.nextPage || 1)}>{t('listings.retry')}</button>
              </p>
            )}
            {feed.loading && feed.listings.length === 0 && <p className="seller-page-status">{t('listings.loading')}</p>}
            {!feed.loading && !feed.error && feed.listings.length === 0 && <p className="seller-page-empty">{t(category === 'equipment' ? 'sellerProfile.noEquipment' : 'sellerProfile.noListings')}</p>}
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
          </section>
          <SellerReviewList sellerId={profile.id} totalReviews={profile.totalReviews} version={reviewsVersion} />
        </div>
      </div>
    </div>
  );
}
