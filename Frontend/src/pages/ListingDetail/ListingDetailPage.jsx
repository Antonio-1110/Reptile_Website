import './ListingDetailPage.css';
import { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import AuctionHistoryCard from './components/AuctionHistoryCard';
import BidPanel from './components/BidPanel';
import BuyNowPanel from './components/BuyNowPanel';
import ContactSellerPanel from './components/ContactSellerPanel';
import OrderPanel from './components/OrderPanel';
import useListingAuction from './useListingAuction';
import AuctionCountdown from '../../components/auctions/AuctionCountdown';
import EmptyState from '../../components/ui/EmptyState';
import Skeleton from '../../components/ui/Skeleton';
import Toast from '../../components/ui/Toast';
import { getListing, getSexKey, isLoggedIn, reportListing } from '../../api/listingsApi';
import { getLocationLabel } from '../../constants/locations';
import { getSpeciesLabel } from '../../constants/species';
import useNow from '../../hooks/useNow';
import { formatMoney, getHeadlinePrice } from '../../utils/auctionFormat';
import { errorText } from '../../utils/errorState';

// The one page for an animal, whether it's for sale at a fixed price or being auctioned. While an
// auction runs (or has ended in a sale) the summary panel shows the auction, including "Buy now" when
// the seller offers a buy-now price. Contact details are only ever shown to the two sides of a paid sale.
export default function ListingDetailPage({ listingId }) {
  const { t, i18n } = useTranslation();
  const language = i18n.resolvedLanguage;
  const now = useNow();
  const [listing, setListing] = useState(null);
  const [loadError, setLoadError] = useState(null);
  const [loadAttempt, setLoadAttempt] = useState(0);
  const [selectedImage, setSelectedImage] = useState(null);
  const [reported, setReported] = useState(false);
  const [reportLoading, setReportLoading] = useState(false);
  const [toast, setToast] = useState(null);
  const [expandedImage, setExpandedImage] = useState(null);
  const toastTimerRef = useRef(null);
  const auctionState = useListingAuction(listingId, now);
  const { auction, bids, phase, order } = auctionState;

  const showToast = (message, tone = 'success') => {
    clearTimeout(toastTimerRef.current);
    setToast({ message, tone });
    toastTimerRef.current = setTimeout(() => setToast(null), 6000);
  };

  useEffect(() => () => clearTimeout(toastTimerRef.current), []);

  useEffect(() => {
    getListing(listingId).then((loadedListing) => {
      setListing(loadedListing);
      setSelectedImage(loadedListing.image);
    }).catch((error) => setLoadError(error.status === 404 ? 'notFound' : 'failed'));
  }, [listingId, loadAttempt]);

  const retryLoad = () => {
    setLoadError(null);
    setLoadAttempt((attempt) => attempt + 1);
  };

  if (loadError) {
    // A 404 means the listing is gone for good; anything else (offline, server error) may pass.
    const notFound = loadError === 'notFound';
    return (
      <div className="listing-detail-missing">
        <div className="listing-detail-missing-inner">
          <EmptyState
            tone={notFound ? 'empty' : 'error'}
            icon={notFound ? '🔍' : undefined}
            title={notFound ? t('listingDetail.notFound') : t('listingDetail.loadError')}
            actions={(
              <>
                {!notFound && <button type="button" className="empty-state-primary" onClick={retryLoad}>{t('listings.retry')}</button>}
                <a href="/marketplace">{t('navigation.backToMarketplace')}</a>
              </>
            )}
          >
            {notFound ? t('listingDetail.notFoundBody') : t('listingDetail.loadErrorBody')}
          </EmptyState>
        </div>
      </div>
    );
  }
  if (listing === null || !auctionState.loaded) {
    return (
      <div className="listing-detail-page">
        <div className="listing-detail-inner">
          <p className="sr-only" role="status">{t('listingDetail.loading')}</p>
          <div className="listing-detail-layout" aria-hidden="true">
            <section className="listing-detail-card listing-detail-gallery">
              <Skeleton className="listing-detail-skeleton-hero" />
            </section>
            <aside className="listing-detail-card listing-detail-summary listing-detail-skeleton-summary">
              <Skeleton style={{ width: '30%', height: '1rem' }} />
              <Skeleton style={{ width: '85%', height: '2rem' }} />
              <Skeleton style={{ width: '50%', height: '1rem' }} />
              <Skeleton style={{ width: '40%', height: '2.25rem' }} />
              <Skeleton style={{ width: '100%', height: '3rem' }} />
            </aside>
          </div>
        </div>
      </div>
    );
  }

  const handleReportListing = async () => {
    if (!isLoggedIn()) {
      showToast(t('listingDetail.toasts.loginToReport'), 'error');
      return;
    }
    setReportLoading(true);
    try {
      await reportListing(listingId);
      setReported(true);
      showToast(t('listingDetail.toasts.reportThanks'));
    } catch (error) {
      showToast(error.message || t('listingDetail.toasts.reportError'), 'error');
    } finally {
      setReportLoading(false);
    }
  };

  const isRunning = phase === 'live' || phase === 'upcoming';
  const soldInAuction = Boolean(auction) && phase === 'ended' && (auction.bidCount > 0 || Boolean(auction.soldVia));
  // An auction that ended without a sale leaves the listing simply for sale again.
  const showAuction = Boolean(auction) && (isRunning || soldInAuction);
  const endedWithoutSale = Boolean(auction) && phase === 'ended' && !soldInAuction;
  const money = (amount) => formatMoney(amount, auction?.currency || 'TWD', language);
  const hasPrice = listing.price != null && listing.price !== '';
  const headline = showAuction && getHeadlinePrice(auction, phase);

  const orMissing = (value, format) => (value == null || value === '' ? t('listingDetail.notProvided') : format(value));
  const facts = [
    [t('listingDetail.seller'), listing.seller],
    [t('filters.location'), getLocationLabel(t, listing.location)],
    [t('listingDetail.age'), orMissing(listing.ageYears, (value) => t('listingDetail.ageValue', { value }))],
    [t('listingDetail.sex'), t(`createListing.sex.${getSexKey(listing.sex)}`)],
    [t('listingDetail.size'), orMissing(listing.size, (value) => t('listingDetail.sizeValue', { value }))],
    [t('listingDetail.weight'), orMissing(listing.weight, (value) => t('listingDetail.weightValue', { value }))],
    [t('listingDetail.shipping'), listing.shippingMethods.length
      ? listing.shippingMethods.map((method) => t(`createListing.shipping.${method}`)).join(t('listingDetail.listSeparator'))
      : t('listingDetail.notProvided')],
    [t('listingDetail.posted'), listing.postedDays === 0 ? t('listingDetail.postedToday') : t('listingDetail.postedValue', { count: listing.postedDays })],
  ];

  return (
    <div className="listing-detail-page">
      <div className="listing-detail-inner">
        <div className="listing-detail-topbar">
          <a href={showAuction ? '/auctions' : '/marketplace'} className="listing-detail-back">
            {showAuction ? t('auctions.detail.back') : t('listingDetail.back')}
          </a>
          <div className="listing-detail-seller-tag">{listing.sellerTag || listing.seller}</div>
        </div>

        <div className="listing-detail-layout">
          <section className="listing-detail-card listing-detail-gallery">
            <div className="listing-detail-hero-frame">
              <button type="button" className="listing-detail-hero-button" onClick={() => setExpandedImage(selectedImage)}>
                <img className="listing-detail-hero-image" src={selectedImage} alt={listing.title} />
              </button>
            </div>

            {listing.gallery.length > 1 && (
              <div className="listing-detail-thumbnails">
                {listing.gallery.map((image, index) => (
                  <button
                    key={image}
                    type="button"
                    onClick={() => setSelectedImage(image)}
                    className={`listing-detail-thumbnail${selectedImage === image ? ' is-selected' : ''}`}
                  >
                    <img src={image} alt={`${listing.title} ${index + 1}`} />
                  </button>
                ))}
              </div>
            )}
          </section>

          <aside className="listing-detail-card listing-detail-summary">
            <div className="listing-detail-summary-top">
              <span className={`listing-detail-kicker${showAuction ? ' listing-detail-kicker--auction' : ''}`}>
                {showAuction ? t('auctions.detail.kicker') : t('listingDetail.forSale')}
              </span>
              <div className="listing-detail-summary-actions">
                <span className="listing-detail-rating">★ {listing.rating}</span>
                <button
                  type="button"
                  onClick={handleReportListing}
                  disabled={reportLoading || reported}
                  className={`listing-detail-report${reported ? ' is-reported' : ''}`}
                >
                  {reported ? t('listingDetail.reported') : t('listingDetail.report')}
                </button>
              </div>
            </div>

            <h1 className="listing-detail-title">{listing.title}</h1>
            <div className="listing-detail-subtitle">
              {getSpeciesLabel(t, listing.species)}
              {listing.lifeStage && <> · {t(`createListing.lifeStages.${listing.lifeStage}`)}</>}
            </div>

            {listing.genes.length > 0 && (
              <div className="listing-detail-genes">
                {listing.genes.map((gene) => <span key={gene} className="listing-detail-gene">{gene}</span>)}
              </div>
            )}

            {auctionState.error && (
              <p className="listing-detail-alert" role="alert">
                {errorText(t, auctionState.error)}{' '}
                <button type="button" className="listing-detail-retry" onClick={auctionState.refresh}>{t('listings.retry')}</button>
              </p>
            )}

            {showAuction ? (
              <>
                <div className="listing-detail-bid-price">
                  <div>
                    <span>{t(headline.labelKey)}</span>
                    <strong>{money(headline.amount)}</strong>
                  </div>
                  <AuctionCountdown auction={auction} now={now} size="large" />
                </div>

                <dl className="listing-detail-stats">
                  <div>
                    <dt>{t('auctions.detail.bids')}</dt>
                    <dd>{auction.bidCount}</dd>
                  </div>
                  {isRunning && (
                    <div>
                      <dt>{t('auctions.detail.nextBid')}</dt>
                      <dd>{money(auction.minimumNextBid)}</dd>
                    </div>
                  )}
                  <div>
                    <dt>{t('auctions.detail.facts.deposit')}</dt>
                    <dd>{money(auction.depositAmount)}</dd>
                  </div>
                </dl>

                {/* After a sale, its buyer and seller follow the order; everyone else sees the result. */}
                {order ? (
                  <OrderPanel order={order} onChanged={auctionState.refresh} onToast={showToast} />
                ) : (
                  <BidPanel
                    auction={auction}
                    phase={phase}
                    topBid={bids.results[0]}
                    hasOwnBid={bids.results.some((bid) => bid.isMine)}
                    onChanged={auctionState.refresh}
                    showToast={showToast}
                  />
                )}

                {isRunning && auction.buyNowAvailable && !auction.isSeller && (
                  <BuyNowPanel auction={auction} onChanged={auctionState.refresh} onToast={showToast} />
                )}
              </>
            ) : (
              <>
                {hasPrice && <div className="listing-detail-price">{money(listing.price)}</div>}
                {endedWithoutSale && <p className="listing-detail-note">{t('listingDetail.auctionEndedNoBids')}</p>}
                <ContactSellerPanel listingId={listingId} onToast={showToast} />
              </>
            )}

            <a
              href={`/marketplace?search=${encodeURIComponent(listing.sellerTag || listing.seller)}`}
              className="listing-detail-more-link"
            >
              {t('listingDetail.moreFromSeller')}
            </a>
          </aside>

          <div className="listing-detail-content">
            {showAuction && (
              <AuctionHistoryCard
                auction={auction}
                bids={bids}
                phase={phase}
                now={now}
                className="listing-detail-card listing-detail-section"
              />
            )}

            <section className="listing-detail-card listing-detail-section listing-detail-about">
              <h2>{t('listingDetail.about')}</h2>
              <p>{listing.description}</p>
              {listing.guideNotes && (
                <div className="listing-detail-care">
                  <h3>{t('listingDetail.care')}</h3>
                  <p>{listing.guideNotes}</p>
                </div>
              )}
            </section>

            <section className="listing-detail-card listing-detail-section">
              <h2>{t('listingDetail.quickFacts')}</h2>
              <dl className="listing-detail-facts-list">
                {facts.map(([label, value]) => (
                  <div key={label} className="listing-detail-fact">
                    <dt>{label}</dt>
                    <dd>{value}</dd>
                  </div>
                ))}
              </dl>
            </section>
          </div>
        </div>

        {expandedImage && (
          <div className="listing-detail-lightbox" onClick={() => setExpandedImage(null)}>
            <div className="listing-detail-lightbox-frame">
              <button type="button" className="listing-detail-lightbox-close" onClick={() => setExpandedImage(null)} aria-label={t('common.dismiss')}>
                ×
              </button>
              <img className="listing-detail-lightbox-image" src={expandedImage} alt={listing.title} />
            </div>
          </div>
        )}
      </div>

      {toast && <Toast message={toast.message} tone={toast.tone} onDismiss={() => setToast(null)} />}
    </div>
  );
}
