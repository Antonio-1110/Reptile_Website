import './BidPanel.css';
import { useState } from 'react';
import useListingTranslation from '../useListingTranslation';
import { isLoggedIn } from '../../../api/authApi';
import { cancelAuction, payDeposit, placeBid } from '../../../api/auctionsApi';
import { formatMoney } from '../../../utils/auctionFormat';

// Quick-pick buttons: the minimum bid and a few increments above it.
const QUICK_PICK_STEPS = [0, 1, 3];

// Deposits in these states no longer let the viewer bid, so they can start a new one.
const PAYABLE_DEPOSIT_STATES = [undefined, 'failed', 'cancelled'];

// Everything the viewer can do on an auction: sign in, pay the deposit, bid, or (as the seller) cancel.
// Calls onChanged() after anything that changes the auction so the page reloads it.
export default function BidPanel({ auction, phase, topBid, hasOwnBid, onChanged, showToast, category }) {
  const { t, i18n } = useListingTranslation(category);
  const money = (amount) => formatMoney(amount, auction.currency, i18n.resolvedLanguage);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [draft, setDraft] = useState('');
  const [confirming, setConfirming] = useState(false);
  const [payment, setPayment] = useState({});

  const minimum = Number(auction.minimumNextBid);
  const increment = Number(auction.minIncrement);
  // Until the user types, the field follows the minimum as other people bid.
  const amountText = draft === '' ? String(minimum) : draft;
  const amount = Number(amountText);
  const amountError = !amountText || Number.isNaN(amount)
    ? t('auctions.bid.enterAmount')
    : amount < minimum ? t('auctions.bid.tooLow', { amount: money(minimum) }) : '';

  const run = async (action) => {
    setBusy(true);
    setError('');
    try {
      await action();
    } catch (requestError) {
      setError(requestError.message);
      // Someone may have outbid us or the auction may have closed: show the latest state, and let the
      // amount follow the new minimum rather than keep a figure that's now too low.
      setDraft('');
      onChanged();
    } finally {
      setBusy(false);
      setConfirming(false);
    }
  };

  const handleDeposit = () => run(async () => {
    const result = await payDeposit(auction.id);
    setPayment(result.payment);
    showToast(t(result.deposit.status === 'held' ? 'auctions.deposit.paidToast' : 'auctions.deposit.pendingToast'));
    onChanged();
  });

  const handleBid = () => run(async () => {
    await placeBid(auction.id, amountText);
    setDraft('');
    showToast(t('auctions.bid.placedToast', { amount: money(amountText) }));
    onChanged();
  });

  const handleCancel = () => run(async () => {
    await cancelAuction(auction.id);
    showToast(t('auctions.seller.cancelledToast'));
    onChanged();
  });

  const errorLine = error && <p className="bid-panel-error" role="alert">{error}</p>;
  const depositStatus = auction.myDeposit?.status;
  const isTopBidder = Boolean(topBid?.isMine);

  if (phase === 'cancelled') {
    return <Panel tone="muted"><p>{t('auctions.result.cancelled')}</p></Panel>;
  }

  if (phase === 'ended') {
    const { key, won } = endedMessage(auction, isTopBidder, hasOwnBid);
    return <Panel tone={won ? 'success' : 'muted'}><p>{t(key, { price: money(auction.soldPrice) })}</p></Panel>;
  }

  if (!isLoggedIn()) {
    const next = encodeURIComponent(`${window.location.pathname}${window.location.search}`);
    return (
      <Panel>
        <p>{t('auctions.signInToBid')}</p>
        <a className="bid-panel-primary" href={`/signin?next=${next}`}>{t('navigation.signIn')}</a>
      </Panel>
    );
  }

  if (auction.isSeller) {
    const canCancel = auction.bidCount === 0;
    return (
      <Panel>
        <p>{t('auctions.seller.yourAuction')}</p>
        {canCancel ? (
          confirming ? (
            <div className="bid-panel-row">
              <button type="button" className="bid-panel-danger" disabled={busy} onClick={handleCancel}>
                {t('auctions.seller.confirmCancel')}
              </button>
              <button type="button" className="bid-panel-secondary" disabled={busy} onClick={() => setConfirming(false)}>
                {t('auctions.keep')}
              </button>
            </div>
          ) : (
            <button type="button" className="bid-panel-secondary" onClick={() => setConfirming(true)}>
              {t('auctions.seller.cancel')}
            </button>
          )
        ) : (
          <p className="bid-panel-hint">{t('auctions.seller.cantCancel')}</p>
        )}
        {errorLine}
      </Panel>
    );
  }

  if (PAYABLE_DEPOSIT_STATES.includes(depositStatus)) {
    return (
      <Panel>
        <h2 className="bid-panel-heading">{t('auctions.deposit.heading')}</h2>
        <p>{t('auctions.deposit.explain', { amount: money(auction.depositAmount) })}</p>
        {depositStatus === 'failed' && <p className="bid-panel-hint">{t('auctions.deposit.failed')}</p>}
        <button type="button" className="bid-panel-primary" disabled={busy} onClick={handleDeposit}>
          {busy ? t('auctions.pleaseWait') : t('auctions.deposit.pay', { amount: money(auction.depositAmount) })}
        </button>
        {errorLine}
      </Panel>
    );
  }

  if (depositStatus === 'pending') {
    return (
      <Panel>
        <h2 className="bid-panel-heading">{t('auctions.deposit.pendingHeading')}</h2>
        <p>{t('auctions.deposit.pending', { amount: money(auction.depositAmount) })}</p>
        {payment.checkout_url && (
          <a className="bid-panel-primary" href={payment.checkout_url}>{t('auctions.deposit.continuePayment')}</a>
        )}
        {errorLine}
      </Panel>
    );
  }

  // Deposit held (or released/captured, which only happens once the auction is over).
  if (phase === 'upcoming') {
    return <Panel><p>{t('auctions.bid.notOpenYet')}</p></Panel>;
  }

  return (
    <Panel tone={isTopBidder ? 'success' : undefined}>
      {isTopBidder && <p className="bid-panel-status bid-panel-status--leading">{t('auctions.bid.leading')}</p>}
      {!isTopBidder && hasOwnBid && <p className="bid-panel-status bid-panel-status--outbid">{t('auctions.bid.outbid')}</p>}

      <form
        className="bid-panel-form"
        onSubmit={(event) => {
          event.preventDefault();
          if (!amountError) setConfirming(true);
        }}
      >
        <label className="bid-panel-label" htmlFor="bid-amount">
          {t('auctions.bid.yourBid')} <span>{t('auctions.bid.minimum', { amount: money(minimum) })}</span>
        </label>
        <div className="bid-panel-row">
          <input
            id="bid-amount"
            className="bid-panel-input"
            type="number"
            inputMode="decimal"
            min={minimum}
            step="any"
            value={amountText}
            aria-invalid={Boolean(amountError)}
            aria-describedby={amountError ? 'bid-amount-error' : undefined}
            onChange={(event) => {
              setDraft(event.target.value);
              setConfirming(false);
            }}
          />
          {!confirming && (
            <button type="submit" className="bid-panel-primary" disabled={busy || Boolean(amountError)}>
              {t('auctions.bid.place')}
            </button>
          )}
        </div>
        {amountError && draft !== '' && <p id="bid-amount-error" className="bid-panel-error">{amountError}</p>}

        <div className="bid-panel-picks">
          {QUICK_PICK_STEPS.map((steps) => {
            const value = minimum + steps * increment;
            return (
              <button
                key={steps}
                type="button"
                className={`bid-panel-pick${amount === value ? ' is-selected' : ''}`}
                onClick={() => {
                  setDraft(String(value));
                  setConfirming(false);
                }}
              >
                {money(value)}
              </button>
            );
          })}
        </div>
      </form>

      {confirming && (
        <div className="bid-panel-confirm">
          <p>{t('auctions.bid.confirmPrompt', { amount: money(amountText) })}</p>
          <div className="bid-panel-row">
            <button type="button" className="bid-panel-primary" disabled={busy} onClick={handleBid}>
              {busy ? t('auctions.pleaseWait') : t('auctions.bid.confirm')}
            </button>
            <button type="button" className="bid-panel-secondary" disabled={busy} onClick={() => setConfirming(false)}>
              {t('auctions.keep')}
            </button>
          </div>
        </div>
      )}
      {errorLine}
      <p className="bid-panel-hint">{t('auctions.deposit.held', { amount: money(auction.depositAmount) })}</p>
      {auction.extendWindowMinutes > 0 && (
        <p className="bid-panel-hint">
          {t('auctions.bid.extendHint', { window: auction.extendWindowMinutes, by: auction.extendByMinutes })}
        </p>
      )}
    </Panel>
  );
}

// What the viewer is told once an auction is over, and whether it's good news for them.
function endedMessage(auction, isTopBidder, hasOwnBid) {
  const purchaseStatus = auction.myPurchase?.status;
  if (auction.soldVia === 'buy_now') {
    if (auction.isSeller) return { key: 'auctions.result.sellerBoughtNow' };
    if (purchaseStatus === 'paid') return { key: 'auctions.result.boughtNow', won: true };
    if (purchaseStatus) return { key: 'auctions.result.buyNowBeaten' };
    if (auction.myDeposit) return { key: 'auctions.result.closedByBuyNow' };
    return { key: 'auctions.result.soldBuyNow' };
  }
  if (auction.isSeller) return { key: auction.bidCount ? 'auctions.result.sellerSold' : 'auctions.result.sellerNoBids' };
  if (isTopBidder) return { key: 'auctions.result.won', won: true };
  if (hasOwnBid) return { key: 'auctions.result.lost' };
  return { key: 'auctions.result.ended' };
}

function Panel({ tone, children }) {
  return <section className={`bid-panel${tone ? ` bid-panel--${tone}` : ''}`}>{children}</section>;
}
