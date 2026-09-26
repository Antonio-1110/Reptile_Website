import './ActionPanels.css';
import { useState } from 'react';
import useListingTranslation from '../useListingTranslation';
import { isLoggedIn } from '../../../api/authApi';
import { startBuyNow } from '../../../api/auctionsApi';
import { formatMoney } from '../../../utils/auctionFormat';

// Buy the animal outright at the seller's buy-now price, paid in full up front. Several buyers may be
// paying at once; the first payment to arrive wins and closes the auction, and later payments are
// refunded in full. The panel says so plainly, and warns when someone else is paying right now.
export default function BuyNowPanel({ auction, onChanged, onToast, category }) {
  const { t, i18n } = useListingTranslation(category);
  const money = (amount) => formatMoney(amount, auction.currency, i18n.resolvedLanguage);
  const price = money(auction.buyNowPrice);
  const [confirming, setConfirming] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [payment, setPayment] = useState({});

  const myPending = auction.myPurchase?.status === 'pending';
  // pendingBuyNowCount includes the viewer's own pending payment.
  const othersPaying = auction.pendingBuyNowCount - (myPending ? 1 : 0);

  const buy = async () => {
    setBusy(true);
    setError('');
    try {
      const result = await startBuyNow(auction.id);
      setPayment(result.payment);
      onToast(t(result.purchase.status === 'paid' ? 'auctions.buyNow.paidToast' : 'auctions.buyNow.pendingToast'));
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusy(false);
      setConfirming(false);
      onChanged();
    }
  };

  const race = othersPaying > 0 && (
    <p className="action-panel-race" role="status">{t('auctions.buyNow.race', { count: othersPaying })}</p>
  );

  return (
    <section className="action-panel-card action-panel-card--buy-now">
      <div className="action-panel-price">
        <span className="action-panel-heading">{t('auctions.buyNow.heading')}</span>
        <strong>{price}</strong>
      </div>

      {myPending ? (
        <>
          <p>{t('auctions.buyNow.pending', { price })}</p>
          {race}
          {payment.checkout_url && (
            <a className="action-panel-primary" href={payment.checkout_url}>{t('auctions.deposit.continuePayment')}</a>
          )}
        </>
      ) : (
        <>
          <p>{t('auctions.buyNow.explain', { price })}</p>
          {race}
          {!isLoggedIn() ? (
            <p>{t('auctions.buyNow.signIn')}</p>
          ) : confirming ? (
            <>
              <p className="action-panel-confirm">{t('auctions.buyNow.confirmPrompt', { price })}</p>
              <div className="action-panel-row">
                <button type="button" className="action-panel-primary" disabled={busy} onClick={buy}>
                  {busy ? t('auctions.pleaseWait') : t('auctions.buyNow.confirm', { price })}
                </button>
                <button type="button" className="action-panel-secondary" disabled={busy} onClick={() => setConfirming(false)}>
                  {t('auctions.keep')}
                </button>
              </div>
            </>
          ) : (
            <button type="button" className="action-panel-secondary" onClick={() => setConfirming(true)}>
              {t('auctions.buyNow.button', { price })}
            </button>
          )}
        </>
      )}
      {error && <p role="alert" className="action-panel-error">{error}</p>}
    </section>
  );
}
