import './AccountMenu.css';
import { useEffect, useId, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router';

// Everything that belongs to the signed-in user, behind one "My account" button so the header keeps
// only a few links. A disclosure (button + list of links) rather than an ARIA menu: the items are
// ordinary links, so Tab moves through them and screen readers announce them as links.
export default function AccountMenu({ onSignOut }) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  const containerRef = useRef(null);
  const buttonRef = useRef(null);
  const listId = useId();

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

  const links = [
    ['/my-listings', t('navigation.myListings')],
    ['/orders', t('myOrders.title')],
    ['/saved', t('accountMenu.savedListings')],
    ['/saved-searches', t('savedSearches.title')],
    ['/settings', t('accountSettings.title')],
  ];

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
        {t('accountMenu.toggle')} <span aria-hidden="true" className="accountMenuCaret">▾</span>
      </button>
      <ul id={listId} className="accountMenuList" hidden={!open}>
        {links.map(([to, label]) => (
          <li key={to}>
            <Link to={to} className="accountMenuItem" onClick={() => setOpen(false)}>{label}</Link>
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
