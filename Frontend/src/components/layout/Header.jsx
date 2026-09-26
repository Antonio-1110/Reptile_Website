import './Header.css';
import { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import LanguageSwitcher from '../ui/LanguageSwitcher';
import AccountMenu from './AccountMenu';
import { isLoggedIn, logout } from '../../api/authApi';
import { getSpeciesLabel } from '../../constants/species';
import { Link, useLocation } from 'react-router';

const SEARCH_OPTIONS = [
  { type: 'species', value: 'Ball Pythons' },
  { type: 'species', value: 'Crested Geckos' },
  { type: 'species', value: 'Leopard Geckos' },
  { type: 'morph', value: 'Pastel' },
  { type: 'morph', value: 'Pied' },
  { type: 'morph', value: 'Lilly White' },
  { type: 'morph', value: 'Enchi' },
  { type: 'morph', value: 'Clown' },
  { type: 'morph', value: 'Tremper Albino' },
  { type: 'morph', value: 'Tangerine' },
];

function Header({ searchTerm = '', setSearchTerm, selectedSearchTags = [], setSelectedSearchTags = () => {}, onSearch = null }) {
  const { t } = useTranslation();
  const location = useLocation();
  const [draftTerm, setDraftTerm] = useState(searchTerm);
  const [draftTags, setDraftTags] = useState(selectedSearchTags);
  // On narrow screens the links live in a drop-down menu (see Header.css); wide screens ignore this.
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef(null);
  const menuButtonRef = useRef(null);

  useEffect(() => {
    if (!menuOpen) return undefined;
    const closeOnEscape = (event) => {
      if (event.key !== 'Escape') return;
      setMenuOpen(false);
      menuButtonRef.current?.focus();
    };
    const closeOnOutsideClick = (event) => {
      if (!menuRef.current?.contains(event.target) && !menuButtonRef.current?.contains(event.target)) setMenuOpen(false);
    };
    document.addEventListener('keydown', closeOnEscape);
    document.addEventListener('pointerdown', closeOnOutsideClick);
    return () => {
      document.removeEventListener('keydown', closeOnEscape);
      document.removeEventListener('pointerdown', closeOnOutsideClick);
    };
  }, [menuOpen]);
  // Species tags keep the backend name as their value but are shown (and matched) in the UI language.
  const tagLabel = (tag) => (tag.type === 'species' ? getSpeciesLabel(t, tag.value) : tag.value);
  const query = draftTerm.trim().toLowerCase();
  const suggestions = query ? SEARCH_OPTIONS.filter((option) => (
    [option.value, tagLabel(option)].some((text) => text.toLowerCase().includes(query))
    && !draftTags.some((tag) => tag.value === option.value)
  )) : [];
  const commitSearch = () => {
    if (onSearch) onSearch(draftTerm, draftTags);
    else {
      setSearchTerm?.(draftTerm);
      setSelectedSearchTags(draftTags);
    }
  };
  const currentPath = `${location.pathname}${location.search}`;
  const signInHref = location.pathname === '/signin' ? currentPath : `/signin?next=${encodeURIComponent(currentPath)}`;
  // Signing out reloads the app rather than navigating, so nothing from the old session lingers.
  const handleSignOut = () => {
    logout();
    window.location.href = '/marketplace';
  };
  const selectSuggestion = (option) => {
    setDraftTags([...draftTags, option]);
    setDraftTerm('');
  };

  return (
    <header className="header">
      <div className="leftSection">
        <Link to="/" className="logo" aria-label="Reptilian">
          <span className="logoRepti">REPTI</span>
          <span className="logoLian">LIAN</span>
        </Link>
        <LanguageSwitcher />
      </div>

      <button
        ref={menuButtonRef}
        type="button"
        className="headerMenuToggle"
        aria-expanded={menuOpen}
        aria-controls="header-menu"
        aria-label={menuOpen ? t('navigation.closeMenu') : t('navigation.menu')}
        onClick={() => setMenuOpen((open) => !open)}
      >
        <span aria-hidden="true">{menuOpen ? '✕' : '☰'}</span>
        <span className="headerMenuToggleLabel">{t('navigation.menu')}</span>
      </button>

      <div className="middleSection">
        <form className="searchForm" onSubmit={(event) => { event.preventDefault(); commitSearch(); }}>
          <div className="searchInputWrapper">
            <div className="searchTags">
              {draftTags.map((tag) => (
                <span key={`${tag.type}-${tag.value}`} className="searchTag">
                  {tagLabel(tag)}
                  <button type="button" onClick={() => setDraftTags(draftTags.filter((item) => item.value !== tag.value))} aria-label={t('search.removeTag', { value: tagLabel(tag) })}>x</button>
                </span>
              ))}
              <input type="text" placeholder={t('search.placeholder')} className="searchBar" value={draftTerm} onChange={(event) => setDraftTerm(event.target.value)} autoComplete="off" />
              <button type="submit" className="searchButton" aria-label={t('search.submit')}>{t('search.submit')}</button>
            </div>
            {suggestions.length > 0 && (
              <div className="searchSuggestions" role="listbox" aria-label={t('search.suggestions')}>
                {suggestions.map((option) => (
                  <button key={`${option.type}-${option.value}`} type="button" role="option" onClick={() => selectSuggestion(option)}>
                    <span>{tagLabel(option)}</span><small>{t(`search.types.${option.type}`)}</small>
                  </button>
                ))}
              </div>
            )}
          </div>
        </form>
      </div>

      <nav id="header-menu" ref={menuRef} className={`rightSection${menuOpen ? ' is-open' : ''}`}
        // Links navigate without a page load, so the open menu has to be closed by hand.
        onClick={(event) => event.target.closest('a') && setMenuOpen(false)}
      >
        <Link to="/auctions" className="headerLink">{t('navigation.auctions')}</Link>
        <button type="button" className="headerLink">{t('navigation.community')}</button>
        {isLoggedIn() ? (
          <>
            <Link to="/postinput" className="headerLink headerPostLink">{t('navigation.postListing')}</Link>
            <AccountMenu onSignOut={handleSignOut} />
          </>
        ) : (
          <>
            <Link to="/postinput" className="headerLink headerPostLink">{t('navigation.postListing')}</Link>
            <Link to={signInHref} className="headerButton">{t('navigation.signIn')}</Link>
          </>
        )}
      </nav>
    </header>
  );
}

export default Header;