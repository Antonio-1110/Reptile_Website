import './InquiriesPage.css';
import { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link, useSearchParams } from 'react-router';
import { getInquiriesPage, isLoggedIn, markInquiryReplied } from '../../api/listingsApi';
import { INQUIRIES_CHANGED } from '../../components/layout/AccountMenu';
import { formatDateTime } from '../../utils/auctionFormat';
import { errorText, toErrorState } from '../../utils/errorState';
import ContactLines from '../ListingDetail/components/ContactLines';

const TABS = ['seller', 'buyer'];

// Contact requests from both sides. Sellers see the buyer's details and mark the inquiry replied once
// they've been in touch (which emails the buyer); buyers see who they asked and whether the seller
// says they've answered. The seller's own details never appear here.
export default function InquiriesPage() {
  const { t, i18n } = useTranslation();
  const language = i18n.resolvedLanguage;
  // Emails link to ?role=seller or ?role=buyer.
  const [searchParams, setSearchParams] = useSearchParams();
  const role = searchParams.get('role') === 'buyer' ? 'buyer' : 'seller';
  const [feed, setFeed] = useState({ inquiries: null, nextPage: 1, loading: true, error: null });
  const [updating, setUpdating] = useState(null);
  const [rowMessage, setRowMessage] = useState({});

  const load = useCallback((page, currentRole) => {
    setFeed((current) => ({ ...current, loading: true, error: null }));
    getInquiriesPage({ role: currentRole, page })
      .then(({ results, hasMore }) => setFeed((current) => ({
        inquiries: page === 1 ? results : [...(current.inquiries || []), ...results],
        nextPage: hasMore ? page + 1 : null,
        loading: false,
        error: null,
      })))
      .catch((error) => setFeed((current) => ({ ...current, loading: false, error: toErrorState(error, 'inquiries.loadError') })));
  }, []);

  useEffect(() => {
    if (!isLoggedIn()) return;
    setFeed({ inquiries: null, nextPage: 1, loading: true, error: null });
    load(1, role);
  }, [load, role]);

  const markReplied = async (inquiry) => {
    setUpdating(inquiry.id);
    setRowMessage((current) => ({ ...current, [inquiry.id]: null }));
    try {
      const updated = await markInquiryReplied(inquiry.id);
      setFeed((current) => ({
        ...current,
        inquiries: current.inquiries.map((item) => (item.id === updated.id ? updated : item)),
      }));
      setRowMessage((current) => ({ ...current, [inquiry.id]: { ok: true } }));
      window.dispatchEvent(new Event(INQUIRIES_CHANGED));
    } catch {
      setRowMessage((current) => ({ ...current, [inquiry.id]: { ok: false } }));
    } finally {
      setUpdating(null);
    }
  };

  if (!isLoggedIn()) {
    return (
      <div className="inquiries-signed-out">
        <h1>{t('inquiries.signedOutTitle')}</h1>
        <Link to={`/signin?next=${encodeURIComponent(`/inquiries?role=${role}`)}`}>{t('auth.signIn')}</Link>
      </div>
    );
  }

  const { inquiries } = feed;
  return (
    <div className="inquiries-page">
      <div className="inquiries-inner">
        <h1>{t('inquiries.title')}</h1>
        <p className="inquiries-subtitle">{t('inquiries.subtitle')}</p>

        <div className="inquiries-tabs" role="tablist" aria-label={t('inquiries.tabsLabel')}>
          {TABS.map((tab) => (
            <button
              key={tab}
              type="button"
              role="tab"
              aria-selected={role === tab}
              className={`inquiries-tab${role === tab ? ' is-selected' : ''}`}
              onClick={() => setSearchParams({ role: tab }, { replace: true })}
            >
              {t(`inquiries.tabs.${tab}`)}
            </button>
          ))}
        </div>

        {feed.error && (
          <p role="alert" className="inquiries-error">
            {errorText(t, feed.error)}{' '}
            <button type="button" className="inquiries-retry" onClick={() => load(inquiries ? feed.nextPage || 1 : 1, role)}>{t('listings.retry')}</button>
          </p>
        )}
        {inquiries === null && feed.loading && <p className="inquiries-status">{t('inquiries.loading')}</p>}
        {inquiries && inquiries.length === 0 && !feed.loading && (
          <div className="inquiries-empty">
            <p>{t(`inquiries.empty.${role}`)}</p>
            {role === 'buyer' && <Link to="/marketplace">{t('inquiries.browse')}</Link>}
          </div>
        )}

        {inquiries && inquiries.length > 0 && (
          <ul className={`inquiries-list${feed.loading ? ' is-refreshing' : ''}`}>
            {inquiries.map((inquiry) => {
              const date = (value) => formatDateTime(value, language);
              const waiting = !inquiry.repliedAt;
              const message = rowMessage[inquiry.id];
              return (
                <li key={inquiry.id} className={`inquiries-row${waiting && role === 'seller' ? ' needs-action' : ''}`}>
                  <div className="inquiries-row-head">
                    <h2><Link to={inquiry.listingPath}>{inquiry.listing.title}</Link></h2>
                    <span className="inquiries-date">{t('inquiries.sentAt', { date: date(inquiry.createdAt) })}</span>
                  </div>

                  {role === 'seller' ? (
                    <>
                      <p className="inquiries-intro">{t('inquiries.receivedIntro')}</p>
                      <ContactLines contact={inquiry.buyer} />
                      {waiting ? (
                        <div className="inquiries-reply">
                          <button type="button" className="inquiries-primary" disabled={updating === inquiry.id} onClick={() => markReplied(inquiry)}>
                            {updating === inquiry.id ? t('auctions.pleaseWait') : t('inquiries.markReplied')}
                          </button>
                          <span className="inquiries-hint">{t('inquiries.markRepliedHint')}</span>
                        </div>
                      ) : (
                        <p className="inquiries-state is-done">{t('inquiries.repliedSeller', { date: date(inquiry.repliedAt) })}</p>
                      )}
                    </>
                  ) : (
                    <>
                      <p className="inquiries-intro">
                        <Link to={`/sellers/${inquiry.seller.id}`}>{t('inquiries.sentTo', { seller: inquiry.seller.displayName })}</Link>
                      </p>
                      <p className={`inquiries-state${waiting ? '' : ' is-done'}`}>
                        {waiting ? t('inquiries.waitingBuyer') : t('inquiries.repliedBuyer', { date: date(inquiry.repliedAt) })}
                      </p>
                    </>
                  )}
                  {message?.ok && <p role="status" className="inquiries-state is-done">{t('inquiries.repliedToast')}</p>}
                  {message && !message.ok && <p role="alert" className="inquiries-error">{t('inquiries.markRepliedError')}</p>}
                </li>
              );
            })}
          </ul>
        )}

        {inquiries && feed.nextPage && !feed.error && (
          <button type="button" className="inquiries-more" disabled={feed.loading} onClick={() => load(feed.nextPage, role)}>
            {feed.loading ? t('inquiries.loading') : t('inquiries.loadMore')}
          </button>
        )}
      </div>
    </div>
  );
}
