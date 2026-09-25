import './AuctionsPage.css';
import { useCallback, useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import AuctionCard from './components/AuctionCard';
import ListingGrid from '../../components/listings/ListingGrid';
import { getAuctionsPage } from '../../api/auctionsApi';
import useNow from '../../hooks/useNow';

const TABS = ['live', 'ended'];
const PREFETCH_MARGIN = '800px';
const emptyFeed = { auctions: [], count: 0, nextPage: 1, loadingPage: 1, failedPage: null };

function readTab() {
  const tab = new URLSearchParams(window.location.search).get('tab');
  return TABS.includes(tab) ? tab : 'live';
}

export default function AuctionsPage() {
  const { t } = useTranslation();
  const now = useNow();
  const [tab, setTab] = useState(readTab);
  const [feed, setFeed] = useState(emptyFeed);
  const tabRef = useRef(tab);
  const sentinelRef = useRef(null);

  // Same paging as MarketplacePage: one page at a time, and responses for a tab the user has
  // already left are dropped.
  const fetchPage = useCallback((page) => {
    setFeed((current) => ({ ...current, loadingPage: page, failedPage: null }));
    getAuctionsPage({ tab, page })
      .then(({ results, count, hasMore }) => {
        if (tabRef.current !== tab) return;
        setFeed((current) => ({
          auctions: page === 1 ? results : [...current.auctions, ...results],
          count,
          nextPage: hasMore ? page + 1 : null,
          loadingPage: null,
          failedPage: null,
        }));
      })
      .catch(() => {
        if (tabRef.current !== tab) return;
        setFeed((current) => ({ ...current, loadingPage: null, failedPage: page }));
      });
  }, [tab]);

  useEffect(() => {
    tabRef.current = tab;
    fetchPage(1);
  }, [tab, fetchPage]);

  useEffect(() => {
    const sentinel = sentinelRef.current;
    if (!sentinel || feed.loadingPage || feed.failedPage || feed.nextPage === null) return undefined;
    const observer = new IntersectionObserver(
      ([entry]) => entry.isIntersecting && fetchPage(feed.nextPage),
      { rootMargin: `0px 0px ${PREFETCH_MARGIN} 0px` },
    );
    observer.observe(sentinel);
    return () => observer.disconnect();
  }, [feed.loadingPage, feed.failedPage, feed.nextPage, fetchPage]);

  const selectTab = (nextTab) => {
    if (nextTab === tab) return;
    window.history.replaceState(null, '', nextTab === 'live' ? '/auctions' : `/auctions?tab=${nextTab}`);
    setFeed(emptyFeed);
    setTab(nextTab);
  };

  const hasAuctions = feed.auctions.length > 0;
  const isFirstLoad = feed.loadingPage === 1 && !hasAuctions;
  const reachedEnd = !feed.loadingPage && !feed.failedPage && feed.nextPage === null;
  const errorKey = feed.failedPage && (feed.failedPage === 1 ? 'auctions.loadError' : 'auctions.loadMoreError');

  return (
    <div className="auctions-page">
      <div className="auctions-inner">
        <header className="auctions-intro">
          <p className="auctions-kicker">{t('auctions.kicker')}</p>
          <h1 className="auctions-title">{t('auctions.title')}</h1>
          <p className="auctions-lead">{t('auctions.intro')}</p>
          <ol className="auctions-steps">
            {['deposit', 'bid', 'result'].map((step, index) => (
              <li key={step} className="auctions-step">
                <span className="auctions-step-number" aria-hidden="true">{index + 1}</span>
                <span>
                  <strong>{t(`auctions.steps.${step}.title`)}</strong>
                  <span>{t(`auctions.steps.${step}.body`)}</span>
                </span>
              </li>
            ))}
          </ol>
        </header>

        <div className="auctions-toolbar">
          <div className="auctions-tabs" role="tablist" aria-label={t('auctions.tabsLabel')}>
            {TABS.map((name) => (
              <button
                key={name}
                type="button"
                role="tab"
                aria-selected={tab === name}
                className={`auctions-tab${tab === name ? ' is-active' : ''}`}
                onClick={() => selectTab(name)}
              >
                {t(`auctions.tabs.${name}`)}
              </button>
            ))}
          </div>
          {!isFirstLoad && !feed.failedPage && (
            <p className="auctions-count">{t('auctions.count', { count: feed.count })}</p>
          )}
        </div>

        <div role="tabpanel" aria-busy={Boolean(feed.loadingPage)}>
          {isFirstLoad && <p className="auctions-status">{t('auctions.loading')}</p>}

          {hasAuctions && (
            <ListingGrid>
              {feed.auctions.map((auction) => <AuctionCard key={auction.id} auction={auction} now={now} />)}
            </ListingGrid>
          )}

          {reachedEnd && !hasAuctions && (
            <div className="auctions-empty">
              <span aria-hidden="true">🦎</span>
              <p>{t(`auctions.empty.${tab}`)}</p>
              <a href="/marketplace">{t('navigation.browseMarketplace')}</a>
            </div>
          )}

          <div ref={sentinelRef} className="auctions-sentinel" aria-hidden="true" />
          {feed.loadingPage > 1 && <p className="auctions-status auctions-status--more" role="status">{t('auctions.loadingMore')}</p>}
          {errorKey && (
            <p className="auctions-status auctions-status--more" role="alert">
              {t(errorKey)}{' '}
              <button type="button" className="auctions-retry" onClick={() => fetchPage(feed.failedPage)}>
                {t('listings.retry')}
              </button>
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
