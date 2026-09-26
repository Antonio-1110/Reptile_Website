import './MyOrdersPage.css';
import { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { getMyOrdersPage } from '../api/auctionsApi';
import { isLoggedIn } from '../api/authApi';
import { formatDateTime, formatMoney } from '../utils/auctionFormat';
import { errorText, toErrorState } from '../utils/errorState';
import { Link } from 'react-router';

const TABS = ['', 'buyer', 'seller'];

// The deadline that matters next for each status, and the order field holding it.
const DEADLINES = {
  offered: 'paymentDueAt',
  awaiting_payment: 'paymentDueAt',
  paid: 'handoverDueAt',
  handed_over: 'confirmDueAt',
};

// Whether the viewer has something to do on the order (the listing page has the buttons).
function needsAction(order) {
  if (order.role === 'buyer') return ['offered', 'awaiting_payment', 'handed_over'].includes(order.status);
  if (order.status === 'paid') return true;
  return order.status === 'buyer_defaulted' && !order.runnerUpDecision && Boolean(order.runnerUpAmount);
}

// The order's actions live on the listing page. Equipment goes through /auctions/:id, which redirects
// to the listing's page.
function orderHref(order) {
  return order.listing.category === 'live_animal' ? `/posts/${order.listing.id}` : `/auctions/${order.auctionId}`;
}

// Every sale the user is part of, as buyer or seller, newest first. Orders used to be visible only on
// the listing page and in emails.
export default function MyOrdersPage() {
  const { t, i18n } = useTranslation();
  const language = i18n.resolvedLanguage;
  const [role, setRole] = useState('');
  const [feed, setFeed] = useState({ orders: null, count: 0, nextPage: 1, loading: true, error: null });

  const load = useCallback((page, currentRole) => {
    setFeed((current) => ({ ...current, loading: true, error: null }));
    getMyOrdersPage({ role: currentRole, page })
      .then(({ results, count, hasMore }) => setFeed((current) => ({
        orders: page === 1 ? results : [...(current.orders || []), ...results],
        count,
        nextPage: hasMore ? page + 1 : null,
        loading: false,
        error: null,
      })))
      .catch((error) => setFeed((current) => ({ ...current, loading: false, error: toErrorState(error, 'myOrders.loadError') })));
  }, []);

  useEffect(() => {
    if (isLoggedIn()) load(1, role);
  }, [load, role]);

  if (!isLoggedIn()) {
    return (
      <div className="my-orders-signed-out">
        <h1>{t('myOrders.signedOutTitle')}</h1>
        <Link to="/signin?next=/orders">{t('auth.signIn')}</Link>
      </div>
    );
  }

  const { orders } = feed;
  return (
    <div className="my-orders-page">
      <div className="my-orders-inner">
        <h1>{t('myOrders.title')}</h1>
        <p className="my-orders-subtitle">{t('myOrders.subtitle')}</p>

        <div className="my-orders-tabs" role="tablist" aria-label={t('myOrders.tabsLabel')}>
          {TABS.map((tab) => (
            <button
              key={tab || 'all'}
              type="button"
              role="tab"
              aria-selected={role === tab}
              className={`my-orders-tab${role === tab ? ' is-selected' : ''}`}
              onClick={() => setRole(tab)}
            >
              {t(`myOrders.tabs.${tab || 'all'}`)}
            </button>
          ))}
        </div>

        {feed.error && (
          <p role="alert" className="my-orders-error">
            {errorText(t, feed.error)}{' '}
            <button type="button" className="my-orders-retry" onClick={() => load(orders ? feed.nextPage || 1 : 1, role)}>{t('listings.retry')}</button>
          </p>
        )}
        {orders === null && feed.loading && <p className="my-orders-status">{t('myOrders.loading')}</p>}
        {orders && orders.length === 0 && !feed.loading && (
          <div className="my-orders-empty">
            <p>{t(`myOrders.empty.${role || 'all'}`)}</p>
            <Link to="/auctions">{t('myOrders.browseAuctions')}</Link>
          </div>
        )}

        {orders && orders.length > 0 && (
          <ul className={`my-orders-list${feed.loading ? ' is-refreshing' : ''}`}>
            {orders.map((order) => {
              const deadlineField = DEADLINES[order.status];
              const deadline = deadlineField && order[deadlineField];
              const actionNeeded = needsAction(order);
              return (
                <li key={order.id} className={`my-orders-row${actionNeeded ? ' needs-action' : ''}`}>
                  <div className="my-orders-row-main">
                    <div className="my-orders-row-tags">
                      <span className="my-orders-role">{t(`myOrders.role.${order.role}`)}</span>
                      {actionNeeded && <span className="my-orders-action">{t('myOrders.actionNeeded')}</span>}
                    </div>
                    <h2><Link to={orderHref(order)}>{order.listing.title}</Link></h2>
                    <p className="my-orders-state">{t(`myOrders.status.${order.role}.${order.status}`)}</p>
                    {deadline && (
                      <p className="my-orders-deadline">
                        {t(`myOrders.deadline.${order.role}.${deadlineField}`, { date: formatDateTime(deadline, language) })}
                      </p>
                    )}
                  </div>
                  <div className="my-orders-row-side">
                    <strong>{formatMoney(order.price, order.currency, language)}</strong>
                    <span>{formatDateTime(order.createdAt, language)}</span>
                    <Link to={orderHref(order)} className="my-orders-open">{t('myOrders.open')}</Link>
                  </div>
                </li>
              );
            })}
          </ul>
        )}

        {orders && feed.nextPage && !feed.error && (
          <button type="button" className="my-orders-more" disabled={feed.loading} onClick={() => load(feed.nextPage, role)}>
            {feed.loading ? t('myOrders.loading') : t('myOrders.loadMore')}
          </button>
        )}
      </div>
    </div>
  );
}
