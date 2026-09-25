import './Header.css';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import LanguageSwitcher from '../ui/LanguageSwitcher';
import { isLoggedIn, logout } from '../../api/authApi';
import { getSpeciesLabel } from '../../constants/species';

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
  const [draftTerm, setDraftTerm] = useState(searchTerm);
  const [draftTags, setDraftTags] = useState(selectedSearchTags);
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
  const currentPath = `${window.location.pathname}${window.location.search}`;
  const signInHref = window.location.pathname === '/signin' ? currentPath : `/signin?next=${encodeURIComponent(currentPath)}`;
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
        <a href="/" className="logo">
          <span className="logoMorph">MORPH</span>
          <span className="logoMarket">MARKET</span>
        </a>
        <LanguageSwitcher />
      </div>

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

      <div className="rightSection">
        <a href="/auctions" className="headerLink">{t('navigation.auctions')}</a>
        <button type="button" className="headerLink">{t('navigation.community')}</button>
        {isLoggedIn() ? (
          <>
            <a href="/my-listings" className="headerLink">{t('navigation.myListings')}</a>
            <a href="/postinput" className="headerLink headerPostLink">{t('navigation.postListing')}</a>
            <a href="/settings" className="headerButton">{t('navigation.account')}</a>
            <button type="button" className="headerLink" onClick={handleSignOut}>{t('navigation.signOut')}</button>
          </>
        ) : (
          <>
            <a href="/postinput" className="headerLink headerPostLink">{t('navigation.postListing')}</a>
            <a href={signInHref} className="headerButton">{t('navigation.signIn')}</a>
          </>
        )}
      </div>
    </header>
  );
}

export default Header;