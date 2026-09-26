import './ActionPanels.css';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import ContactLines from './ContactLines';
import { getContactPreview, isLoggedIn, requestSellerContact } from '../../../api/listingsApi';
import { Link } from 'react-router';

// "Contact seller" on a fixed-price listing. The seller's details are never shown (that's what
// scrapers are after); instead the buyer reviews their own details, we pass them on, and the seller
// gets in touch.
export default function ContactSellerPanel({ listingId, category, onToast }) {
  const { t } = useTranslation();
  const [preview, setPreview] = useState(null);
  const [sent, setSent] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const run = async (action) => {
    setError('');
    setLoading(true);
    try {
      await action();
    } catch (requestError) {
      setError(requestError.message || t('listingDetail.toasts.contactError'));
    } finally {
      setLoading(false);
    }
  };

  const openPreview = () => run(async () => {
    const result = await getContactPreview(listingId, category);
    setPreview(result.contact);
    setSent(result.already_sent);
  });

  const send = () => run(async () => {
    await requestSellerContact(listingId, category);
    setSent(true);
    onToast(t('listingDetail.contact.sentToast'));
  });

  if (!isLoggedIn()) return <div className="action-panel-hint">{t('listingDetail.loginToContact')}</div>;

  if (!preview) {
    return (
      <>
        <button type="button" onClick={openPreview} disabled={loading} className="action-panel-primary">
          {loading ? t('auctions.pleaseWait') : t('listingDetail.contactSeller')}
        </button>
        {error && <p role="alert" className="action-panel-error">{error}</p>}
      </>
    );
  }

  return (
    <section className="action-panel-card">
      <div className="action-panel-heading">
        {sent ? t('listingDetail.contact.sentHeading') : t('listingDetail.contact.previewHeading')}
      </div>
      <p>{sent ? t('listingDetail.contact.sentIntro') : t('listingDetail.contact.previewIntro')}</p>
      <ContactLines contact={preview} />
      {!sent && (
        <>
          <p className="action-panel-small">
            {t('listingDetail.contact.wrongDetails')} <Link to="/settings">{t('listingDetail.contact.editDetails')}</Link>
          </p>
          <div className="action-panel-row">
            <button type="button" className="action-panel-primary" disabled={loading} onClick={send}>
              {loading ? t('auctions.pleaseWait') : t('listingDetail.contact.send')}
            </button>
            <button type="button" className="action-panel-secondary" disabled={loading} onClick={() => setPreview(null)}>
              {t('auctions.keep')}
            </button>
          </div>
        </>
      )}
      {error && <p role="alert" className="action-panel-error">{error}</p>}
    </section>
  );
}
