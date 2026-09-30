import './AlertsPage.css';
import { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router';
import { getAlertsPage, markAllAlertsRead } from '../../api/alertsApi';
import { isLoggedIn } from '../../api/listingsApi';
import { ALERTS_CHANGED } from '../../components/layout/AccountMenu';
import usePageMeta from '../../hooks/usePageMeta';
import { formatDateTime } from '../../utils/auctionFormat';
import { errorText, toErrorState } from '../../utils/errorState';

// The user's site alerts, newest first. Opening the page counts as reading them: they're marked read
// once shown (so they stay out of the summary email), but keep their "New" tag until the next visit.
export default function AlertsPage() {
  const { t, i18n } = useTranslation();
  usePageMeta(t('alerts.title'));
  const language = i18n.resolvedLanguage;
  const [feed, setFeed] = useState({ alerts: null, nextPage: 1, loading: true, error: null });

  const load = useCallback((page) => {
    setFeed((current) => ({ ...current, loading: true, error: null }));
    getAlertsPage(page)
      .then(({ results, hasMore }) => {
        setFeed((current) => ({
          alerts: page === 1 ? results : [...(current.alerts || []), ...results],
          nextPage: hasMore ? page + 1 : null,
          loading: false,
          error: null,
        }));
        if (results.some((alert) => !alert.isRead)) {
          markAllAlertsRead().then(() => window.dispatchEvent(new Event(ALERTS_CHANGED))).catch(() => {});
        }
      })
      .catch((error) => setFeed((current) => ({ ...current, loading: false, error: toErrorState(error, 'alerts.loadError') })));
  }, []);

  useEffect(() => {
    if (isLoggedIn()) load(1);
  }, [load]);

  if (!isLoggedIn()) {
    return (
      <div className="alerts-page">
        <div className="alerts-inner">
          <h1>{t('alerts.signedOutTitle')}</h1>
          <Link to={`/signin?next=${encodeURIComponent('/alerts')}`}>{t('auth.signIn')}</Link>
        </div>
      </div>
    );
  }

  const { alerts } = feed;
  return (
    <div className="alerts-page">
      <div className="alerts-inner">
        <h1>{t('alerts.title')}</h1>
        <p className="alerts-subtitle">{t('alerts.subtitle')}</p>
        <p className="alerts-note">{t('alerts.emailNote')}</p>

        {feed.error && (
          <p role="alert" className="alerts-error">
            {errorText(t, feed.error)}{' '}
            <button type="button" className="alerts-button" onClick={() => load(alerts ? feed.nextPage || 1 : 1)}>{t('listings.retry')}</button>
          </p>
        )}
        {alerts === null && feed.loading && <p className="alerts-status" role="status">{t('alerts.loading')}</p>}
        {alerts && alerts.length === 0 && (
          <div className="alerts-empty">
            <p>{t('alerts.empty')}</p>
            <Link to="/marketplace">{t('alerts.browse')}</Link>
          </div>
        )}

        {alerts && alerts.length > 0 && (
          <ul className="alerts-list">
            {alerts.map((alert) => (
              <li key={alert.id} className={`alerts-row${alert.isRead ? '' : ' is-new'}`}>
                <div className="alerts-row-head">
                  <h2>
                    {!alert.isRead && <span className="alerts-new">{t('alerts.new')}</span>}
                    {alert.title}
                  </h2>
                  <time dateTime={alert.createdAt.toISOString()}>{formatDateTime(alert.createdAt, language)}</time>
                </div>
                <p className="alerts-body">{alert.body}</p>
                {alert.link && <Link className="alerts-open" to={alert.link}>{t('alerts.open')}</Link>}
              </li>
            ))}
          </ul>
        )}

        {alerts && feed.nextPage && !feed.error && (
          <button type="button" className="alerts-button alerts-more" disabled={feed.loading} onClick={() => load(feed.nextPage)}>
            {t('alerts.loadMore')}
          </button>
        )}
      </div>
    </div>
  );
}
