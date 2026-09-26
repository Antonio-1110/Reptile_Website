import './ActionPanels.css';
import { useState } from 'react';
import useListingTranslation from '../useListingTranslation';
import ContactLines from './ContactLines';
import {
  confirmReceived, decideRunnerUp, declineOffer, markHandedOver, payOrder, reportProblem,
} from '../../../api/auctionsApi';
import { formatDateTime, formatMoney } from '../../../utils/auctionFormat';

// Statuses where the order is over, one way or another; the rest are still in progress.
const CLOSED = ['completed', 'buyer_defaulted', 'declined', 'seller_defaulted', 'refunded'];

// Where a sale stands after the auction, for its buyer or seller: what happens next, by when, and the
// one action (if any) that's theirs to take. Everything is enforced by the backend (auction/orders.py).
export default function OrderPanel({ order, onChanged, onToast, category }) {
  const { t, i18n } = useListingTranslation(category);
  const language = i18n.resolvedLanguage;
  const values = {
    price: formatMoney(order.price, order.currency, language),
    balance: formatMoney(order.balance, order.currency, language),
    deposit: formatMoney(order.depositAmount, order.currency, language),
    payout: formatMoney(order.payout, order.currency, language),
    runnerUp: formatMoney(order.runnerUpAmount, order.currency, language),
    paymentDue: order.paymentDueAt && formatDateTime(order.paymentDueAt, language),
    handoverDue: order.handoverDueAt && formatDateTime(order.handoverDueAt, language),
    confirmDue: order.confirmDueAt && formatDateTime(order.confirmDueAt, language),
    note: order.handoverNote || '—',
    problem: order.problemReport,
  };
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [note, setNote] = useState('');
  const [problem, setProblem] = useState('');
  const [step, setStep] = useState(null); // 'confirm' or 'report' while the buyer is deciding

  const run = async (action, toastKey) => {
    setBusy(true);
    setError('');
    try {
      await action();
      if (toastKey) onToast(t(toastKey));
      setStep(null);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusy(false);
      onChanged();
    }
  };

  const buyer = order.role === 'buyer';
  // Text key: auctions.order.<role>.<status> (a couple of statuses depend on more than that).
  let messageKey = `auctions.order.${order.role}.${order.status}`;
  if (buyer && order.status === 'awaiting_payment' && order.balanceStatus === 'pending') messageKey = 'auctions.order.buyer.paymentPending';
  if (!buyer && order.status === 'buyer_defaulted') {
    if (order.runnerUpDecision) messageKey = `auctions.order.seller.runnerUp.${order.runnerUpDecision}`;
    else if (!order.runnerUpAmount) messageKey = 'auctions.order.seller.defaultedNoRunnerUp';
  }

  const primary = (label, onClick) => (
    <button type="button" className="action-panel-primary" disabled={busy} onClick={onClick}>
      {busy ? t('auctions.pleaseWait') : label}
    </button>
  );
  const secondary = (label, onClick) => (
    <button type="button" className="action-panel-secondary" disabled={busy} onClick={onClick}>{label}</button>
  );

  let actions = null;
  if (buyer && order.status === 'awaiting_payment' && order.balanceStatus !== 'pending') {
    actions = primary(t('auctions.order.pay', values), () => run(() => payOrder(order.id), 'auctions.order.paidToast'));
  } else if (buyer && order.status === 'offered' && order.balanceStatus !== 'pending') {
    actions = (
      <div className="action-panel-row">
        {primary(t('auctions.order.acceptOffer', values), () => run(() => payOrder(order.id), 'auctions.order.paidToast'))}
        {secondary(t('auctions.order.declineOffer'), () => run(() => declineOffer(order.id)))}
      </div>
    );
  } else if (!buyer && order.status === 'paid') {
    actions = (
      <>
        <label className="action-panel-label" htmlFor="handover-note">{t('auctions.order.noteLabel')}</label>
        <input
          id="handover-note"
          className="action-panel-input"
          maxLength={300}
          placeholder={t('auctions.order.notePlaceholder')}
          value={note}
          onChange={(event) => setNote(event.target.value)}
        />
        {primary(t('auctions.order.markHandedOver'), () => run(() => markHandedOver(order.id, note), 'auctions.order.handedOverToast'))}
      </>
    );
  } else if (buyer && order.status === 'handed_over') {
    if (step === 'confirm') {
      actions = (
        <>
          <p className="action-panel-confirm">{t('auctions.order.confirmPrompt')}</p>
          <div className="action-panel-row">
            {primary(t('auctions.order.confirmYes'), () => run(() => confirmReceived(order.id), 'auctions.order.completedToast'))}
            {secondary(t('auctions.keep'), () => setStep(null))}
          </div>
        </>
      );
    } else if (step === 'report') {
      actions = (
        <>
          <label className="action-panel-label" htmlFor="order-problem">{t('auctions.order.problemLabel')}</label>
          <textarea
            id="order-problem"
            className="action-panel-input"
            rows={3}
            maxLength={2000}
            value={problem}
            onChange={(event) => setProblem(event.target.value)}
          />
          <div className="action-panel-row">
            {primary(t('auctions.order.sendProblem'), () => run(() => reportProblem(order.id, problem), 'auctions.order.problemToast'))}
            {secondary(t('auctions.keep'), () => setStep(null))}
          </div>
        </>
      );
    } else {
      actions = (
        <div className="action-panel-row">
          {primary(t('auctions.order.confirmReceived'), () => setStep('confirm'))}
          {secondary(t('auctions.order.reportProblem'), () => setStep('report'))}
        </div>
      );
    }
  } else if (!buyer && order.status === 'buyer_defaulted' && !order.runnerUpDecision && order.runnerUpAmount) {
    actions = (
      <div className="action-panel-row">
        {primary(t('auctions.order.offerRunnerUp', values), () => run(() => decideRunnerUp(order.id, true), 'auctions.order.offeredToast'))}
        {secondary(t('auctions.order.keepAnimal'), () => run(() => decideRunnerUp(order.id, false)))}
      </div>
    );
  }

  const tone = order.status === 'completed' ? ' action-panel-card--success' : CLOSED.includes(order.status) ? '' : ' action-panel-card--buy-now';
  return (
    <section className={`action-panel-card${tone}`}>
      <div className="action-panel-heading">{t(`auctions.order.heading.${order.role}`)}</div>
      <p>{t(messageKey, values)}</p>
      {actions}
      {error && <p role="alert" className="action-panel-error">{error}</p>}
      {order.counterpart && (
        <>
          <div className="action-panel-heading action-panel-subheading">
            {t(buyer ? 'auctions.deal.heading.buyer' : 'auctions.deal.heading.seller')}
          </div>
          <ContactLines contact={order.counterpart} />
          <p className="action-panel-small">{t(buyer ? 'auctions.deal.note.buyer' : 'auctions.deal.note.seller')}</p>
        </>
      )}
    </section>
  );
}
