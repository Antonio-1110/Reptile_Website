import './MyListingsPage.css';
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import Toast from '../components/ui/Toast';
import { errorText, toErrorState } from '../utils/errorState';
import { deleteListing, getMyListings, isLoggedIn } from '../api/listingsApi';

export default function MyListingsPage() {
  const { t } = useTranslation();
  const [listings, setListings] = useState(null);
  const [error, setError] = useState(null);
  const [deletingId, setDeletingId] = useState(null);
  const [toast, setToast] = useState(null);

  const loadListings = () => {
    getMyListings()
      .then(setListings)
      .catch((loadError) => setError(toErrorState(loadError, 'myListings.loadError')));
  };

  useEffect(() => {
    loadListings();
  }, []);

  const handleDelete = async (listing) => {
    if (!window.confirm(t('myListings.confirmDelete', { title: listing.title }))) return;
    setDeletingId(listing.id);
    try {
      await deleteListing(listing.id, listing.category);
      setListings((current) => current.filter((item) => !(item.id === listing.id && item.category === listing.category)));
      setToast({ tone: 'success', message: t('myListings.deleted', { title: listing.title }) });
    } catch (deleteError) {
      setToast({ tone: 'error', message: deleteError.message || t('myListings.deleteError') });
    } finally {
      setDeletingId(null);
    }
  };

  if (!isLoggedIn()) {
    return (
      <div className="my-listings-signed-out">
        <div className="my-listings-signed-out-inner">
          <h1>{t('myListings.signedOutTitle')}</h1>
          <a href="/signin?next=/my-listings">{t('auth.signIn')}</a>
        </div>
      </div>
    );
  }

  return (
    <div className="my-listings-page">
      <div className="my-listings-inner">
        <div className="my-listings-header">
          <div>
            <h1>{t('navigation.myListings')}</h1>
            <p>{t('myListings.subtitle')}</p>
          </div>
          <div className="my-listings-header-links">
            <a href="/orders" className="my-listings-orders">{t('myListings.orders')}</a>
            <a href="/postinput" className="my-listings-new">
              {t('myListings.newListing')}
            </a>
          </div>
        </div>

        {error && <p role="alert" className="my-listings-error">{errorText(t, error)}</p>}
        {!error && listings === null && <p className="my-listings-status">{t('myListings.loading')}</p>}
        {!error && listings && listings.length === 0 && (
          <div className="my-listings-empty">
            {t('myListings.empty')}
          </div>
        )}

        {listings && listings.length > 0 && (
          <div className="my-listings-list">
            {listings.map((listing) => (
              <div key={`${listing.category}-${listing.id}`} className="my-listings-row">
                <div>
                  <div className="my-listings-row-heading">
                    <span className="my-listings-category">
                      {t(`myListings.categories.${listing.category}`, { defaultValue: listing.category })}
                    </span>
                    <h2>{listing.title}</h2>
                  </div>
                  <p className="my-listings-price">${listing.price ?? '—'}</p>
                </div>
                <div className="my-listings-actions">
                  <a href={`/postinput?edit=${listing.id}&category=${listing.category}`} className="my-listings-edit">
                    {t('myListings.edit')}
                  </a>
                  <button
                    type="button"
                    onClick={() => handleDelete(listing)}
                    disabled={deletingId === listing.id}
                    className="my-listings-delete"
                  >
                    {deletingId === listing.id ? t('myListings.deleting') : t('myListings.delete')}
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {toast && <Toast message={toast.message} tone={toast.tone} onDismiss={() => setToast(null)} />}
    </div>
  );
}
