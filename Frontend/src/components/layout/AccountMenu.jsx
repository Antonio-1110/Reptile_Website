import './AccountMenu.css';
import { useEffect, useId, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link, useLocation } from 'react-router';
import { getUnreadAlertCount } from '../../api/alertsApi';
import { getWaitingInquiryCount } from '../../api/listingsApi';
import useFeature from '../../hooks/useFeature';

// Fired by the Inquiries page after the seller marks one replied, so the count here drops at once.
export const INQUIRIES_CHANGED = 'reptilian:inquiries-changed';
// Fired by the Alerts page once it has marked the alerts read.
export const ALERTS_CHANGED = 'reptilian:alerts-changed';

// Everything that belongs to the signed-in user, behind one "My account" button so the header keeps
// only a few links. A disclosure (button + list of links) rather than an ARIA menu: the items are
// ordinary links, so Tab moves through them and screen readers announce them as links.
export default function AccountMenu({ onSignOut }) {
  const { t } = useTranslation();
  const auctionsOn = useFeature('auctions');
  const [open, setOpen] = useState(false);
  const containerRef = useRef(null);
  const buttonRef = useRef(null);
  const listId = useId();
  const { pathname } = useLocation();
  const [waiting, setWaiting] = useState(0);
  const [unreadAlerts, setUnreadAlerts] = useState(0);

  // Inquiries (#91) and most alerts (#59) reach users only on the site, so the menu shows how many are
  // waiting. Small count queries per page change; a failure just leaves a badge as it was.
  useEffect(() => {
    let active = true;
    const refreshInquiries = () => getWaitingInquiryCount()
      .then((count) => active && setWaiting(count))
      .catch(() => {});
    const refreshAlerts = () => getUnreadAlertCount()
      .then((count) => active && setUnreadAlerts(count))
      .catch(() => {});
    refreshInquiries();
    refreshAlerts();
    window.addEventListener(INQUIRIES_CHANGED, refreshInquiries);
    window.addEventListener(ALERTS_CHANGED, refreshAlerts);
    return () => {
      active = false;
      window.removeEventListener(INQUIRIES_CHANGED, refreshInquiries);
      window.removeEventListener(ALERTS_CHANGED, refreshAlerts);
    };
  }, [pathname]);

  useEffect(() => {
    if (!open) return undefined;
    const closeOnEscape = (event) => {
      if (event.key !== 'Escape') return;
      // The header's own menu (narrow screens) also closes on Escape; this one goes first.
      event.stopPropagation();
      setOpen(false);
      buttonRef.current?.focus();
    };
    const closeOnOutsideClick = (event) => {
      if (!containerRef.current?.contains(event.target)) setOpen(false);
    };
    // Focus leaving the menu (Tab past the last item) closes it, like a click elsewhere.
    const closeOnFocusOut = (event) => {
      if (!containerRef.current?.contains(event.target)) setOpen(false);
    };
    document.addEventListener('keydown', closeOnEscape, true);
    document.addEventListener('pointerdown', closeOnOutsideClick);
    document.addEventListener('focusin', closeOnFocusOut);
    return () => {
      document.removeEventListener('keydown', closeOnEscape, true);
      document.removeEventListener('pointerdown', closeOnOutsideClick);
      document.removeEventListener('focusin', closeOnFocusOut);
    };
  }, [open]);

  // Orders only come from auctions and buy now, so the page goes with the auctions switch.
  const links = [
    ['/alerts', t('alerts.title')],
    ['/my-listings', t('navigation.myListings')],
    auctionsOn && ['/orders', t('myOrders.title')],
    ['/inquiries', t('inquiries.title')],
    ['/saved', t('accountMenu.savedListings')],
    ['/saved-searches', t('savedSearches.title')],
    ['/settings', t('accountSettings.title')],
  ].filter(Boolean);

  return (
    <div ref={containerRef} className={`accountMenu${open ? ' is-open' : ''}`}>
      <button
        ref={buttonRef}
        type="button"
        className="accountMenuToggle"
        aria-expanded={open}
        aria-controls={listId}
        onClick={() => setOpen((value) => !value)}
      >
        {t('accountMenu.toggle')}
        {waiting + unreadAlerts > 0 && (
          <span className="accountMenuBadge">
            <span aria-hidden="true">{waiting + unreadAlerts}</span>
            <span className="accountMenuSr">
              {[
                waiting > 0 && t('inquiries.waitingCount', { count: waiting }),
                unreadAlerts > 0 && t('alerts.unreadCount', { count: unreadAlerts }),
              ].filter(Boolean).join(', ')}
            </span>
          </span>
        )}
        <span aria-hidden="true" className="accountMenuCaret">▾</span>
      </button>
      <ul id={listId} className="accountMenuList" hidden={!open}>
        {links.map(([to, label]) => (
          <li key={to}>
            <Link to={to} className="accountMenuItem" onClick={() => setOpen(false)}>
              {label}
              {to === '/inquiries' && waiting > 0 && (
                <span className="accountMenuBadge">
                  <span aria-hidden="true">{waiting}</span>
                  <span className="accountMenuSr">{t('inquiries.waitingCount', { count: waiting })}</span>
                </span>
              )}
              {to === '/alerts' && unreadAlerts > 0 && (
                <span className="accountMenuBadge">
                  <span aria-hidden="true">{unreadAlerts}</span>
                  <span className="accountMenuSr">{t('alerts.unreadCount', { count: unreadAlerts })}</span>
                </span>
              )}
            </Link>
          </li>
        ))}
        <li className="accountMenuDivider" aria-hidden="true" />
        <li>
          <button type="button" className="accountMenuItem" onClick={onSignOut}>{t('navigation.signOut')}</button>
        </li>
      </ul>
    </div>
  );
}
