import './StartAuctionPage.css';
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { createAuction, getAuctionRules, getSellerBond, paySellerBond } from '../../api/auctionsApi';
import { getCurrentProfile, getRawListing } from '../../api/listingsApi';
import { formatMoney } from '../../utils/auctionFormat';
import { errorText, toErrorState } from '../../utils/errorState';

const DEFAULT_DAYS = 7;
const DEFAULT_INCREMENT = '100';

// <input type="datetime-local"> works in local time without a zone: "2026-09-30T18:00".
function toLocalInput(date) {
  const pad = (value) => String(value).padStart(2, '0');
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

function inDays(days) {
  const date = new Date(Date.now() + days * 86400000);
  date.setSeconds(0, 0);
  return date;
}

// Early feedback only: the API checks all of this (and more) again.
function validate(form, rules, t) {
  const errors = {};
  const start = form.startMode === 'later' ? new Date(form.startsAt) : new Date();
  const end = new Date(form.endsAt);
  if (!(Number(form.startingPrice) > 0)) errors.starting_price = t('startAuction.errors.startingPrice');
  if (!(Number(form.minIncrement) > 0)) errors.min_increment = t('startAuction.errors.minIncrement');
  if (form.startMode === 'later' && (Number.isNaN(start.getTime()) || start < new Date())) errors.starts_at = t('startAuction.errors.startsAt');
  const hours = (end - start) / 3600000;
  if (Number.isNaN(end.getTime())) errors.ends_at = t('startAuction.errors.endsAt');
  else if (hours < rules.minDurationHours) errors.ends_at = t('startAuction.errors.tooShort', { count: rules.minDurationHours });
  else if (hours > rules.maxDurationDays * 24) errors.ends_at = t('startAuction.errors.tooLong', { count: rules.maxDurationDays });
  if (form.buyNowPrice !== '' && !(Number(form.buyNowPrice) > Number(form.startingPrice))) errors.buy_now_price = t('startAuction.errors.buyNow');
  return errors;
}

// Puts one of the seller's listings up for auction (paid commercial accounts), after the seller bond
// when one is required. Reached from My Listings: /auctions/new?listing=<id>&category=<category>.
export default function StartAuctionPage({ listingId, category }) {
  const { t, i18n } = useTranslation();
  const language = i18n.resolvedLanguage;
  const [state, setState] = useState({ loading: true, error: null, profile: null, rules: null, bond: null, listing: null });
  const [form, setForm] = useState(null);
  const [fieldErrors, setFieldErrors] = useState({});
  const [submitError, setSubmitError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [bondBusy, setBondBusy] = useState(false);
  const [bondPayment, setBondPayment] = useState({});

  useEffect(() => {
    Promise.all([getCurrentProfile(), getAuctionRules(), getSellerBond(), getRawListing(listingId, category)])
      .then(([profile, rules, bond, listing]) => {
        setState({ loading: false, error: null, profile, rules, bond, listing });
        setForm({
          startingPrice: listing.price != null ? String(Math.round(Number(listing.price))) : '',
          minIncrement: DEFAULT_INCREMENT,
          startMode: 'now',
          startsAt: toLocalInput(inDays(1)),
          endsAt: toLocalInput(inDays(DEFAULT_DAYS)),
          buyNowPrice: '',
        });
      })
      .catch((error) => setState((current) => ({ ...current, loading: false, error: toErrorState(error, 'startAuction.loadError') })));
  }, [listingId, category]);

  const { loading, error, profile, rules, bond, listing } = state;
  const money = (amount) => formatMoney(amount, rules?.currency, language);
  const listingHref = category === 'equipment' ? '/my-listings' : `/posts/${listingId}`;

  if (loading) return <div className="start-auction-page"><p className="start-auction-status">{t('startAuction.loading')}</p></div>;
  if (error) {
    return (
      <div className="start-auction-page">
        <div className="start-auction-card">
          <p role="alert" className="start-auction-error">{errorText(t, error)}</p>
          <a href="/my-listings">{t('startAuction.backToListings')}</a>
        </div>
      </div>
    );
  }

  const header = (
    <>
      <a href="/my-listings" className="start-auction-back">{t('startAuction.backToListings')}</a>
      <h1>{t('startAuction.title')}</h1>
      <p className="start-auction-listing">{listing.title}</p>
    </>
  );

  if (!profile.can_start_auction) {
    return (
      <div className="start-auction-page">
        <div className="start-auction-card">
          {header}
          <p>{t('startAuction.paidOnly')}</p>
          <a href="/upgrade" className="start-auction-primary">{t('startAuction.seePlans')}</a>
        </div>
      </div>
    );
  }

  const bondStatus = bond.bond?.status;
  if (bond.required && bondStatus !== 'held') {
    const payBond = async () => {
      setBondBusy(true);
      setSubmitError('');
      try {
        const result = await paySellerBond();
        setBondPayment(result.payment);
        setState((current) => ({ ...current, bond: { ...current.bond, bond: result.bond } }));
      } catch (bondError) {
        setSubmitError(bondError.message);
      } finally {
        setBondBusy(false);
      }
    };
    return (
      <div className="start-auction-page">
        <div className="start-auction-card">
          {header}
          <h2>{t('startAuction.bond.heading')}</h2>
          <p>{t('startAuction.bond.explain', { amount: money(bond.amount) })}</p>
          {bondStatus === 'forfeited' && <p className="start-auction-note">{t('startAuction.bond.forfeited')}</p>}
          {bondStatus === 'failed' && <p className="start-auction-note">{t('startAuction.bond.failed')}</p>}
          {bondStatus === 'pending' ? (
            <>
              <p className="start-auction-note" role="status">{t('startAuction.bond.pending')}</p>
              {bondPayment.checkout_url && <a className="start-auction-primary" href={bondPayment.checkout_url}>{t('startAuction.bond.continuePayment')}</a>}
            </>
          ) : (
            <button type="button" className="start-auction-primary" disabled={bondBusy} onClick={payBond}>
              {bondBusy ? t('auctions.pleaseWait') : t('startAuction.bond.pay', { amount: money(bond.amount) })}
            </button>
          )}
          {submitError && <p role="alert" className="start-auction-error">{submitError}</p>}
        </div>
      </div>
    );
  }

  // name: the form field; key: the API field whose error it clears.
  const update = (name, key) => (event) => {
    setForm((current) => ({ ...current, [name]: event.target.value }));
    if (key) setFieldErrors((current) => ({ ...current, [key]: undefined }));
  };

  const deposit = Math.max(Number(form.startingPrice || 0) * rules.depositRate, rules.minDeposit);

  const submit = async (event) => {
    event.preventDefault();
    setSubmitError('');
    const errors = validate(form, rules, t);
    setFieldErrors(errors);
    if (Object.keys(errors).length) return;
    setSubmitting(true);
    try {
      await createAuction({
        category,
        listingId,
        startingPrice: form.startingPrice,
        minIncrement: form.minIncrement,
        startsAt: form.startMode === 'later' ? new Date(form.startsAt) : null,
        endsAt: new Date(form.endsAt),
        buyNowPrice: form.buyNowPrice,
      });
      window.location.href = category === 'equipment' ? '/auctions' : `/posts/${listingId}`;
    } catch (createError) {
      setFieldErrors(createError.fields || {});
      const fieldKeys = ['starting_price', 'min_increment', 'starts_at', 'ends_at', 'buy_now_price'];
      const onFields = Object.keys(createError.fields || {}).some((key) => fieldKeys.includes(key));
      setSubmitError(onFields ? t('startAuction.errors.fixFields') : createError.message);
      setSubmitting(false);
    }
  };

  const field = (name, key, input, hint) => (
    <div className="start-auction-field">
      <label htmlFor={`auction-${name}`}>{t(`startAuction.fields.${name}`)}</label>
      {input}
      {hint && <p className="start-auction-hint">{hint}</p>}
      {fieldErrors[key] && <p id={`auction-${name}-error`} className="start-auction-field-error">{fieldErrors[key]}</p>}
    </div>
  );
  const invalid = (key, name) => ({ 'aria-invalid': Boolean(fieldErrors[key]), 'aria-describedby': fieldErrors[key] ? `auction-${name}-error` : undefined });

  return (
    <div className="start-auction-page">
      <form className="start-auction-card" onSubmit={submit} noValidate>
        {header}
        <p className="start-auction-intro">{t('startAuction.intro')}</p>

        <div className="start-auction-grid">
          {field('startingPrice', 'starting_price',
            <input id="auction-startingPrice" type="number" inputMode="decimal" min="1" step="any" value={form.startingPrice} onChange={update('startingPrice', 'starting_price')} {...invalid('starting_price', 'startingPrice')} />,
            t('startAuction.depositHint', { amount: money(deposit) }))}
          {field('minIncrement', 'min_increment',
            <input id="auction-minIncrement" type="number" inputMode="decimal" min="1" step="any" value={form.minIncrement} onChange={update('minIncrement', 'min_increment')} {...invalid('min_increment', 'minIncrement')} />,
            t('startAuction.incrementHint'))}
        </div>

        <fieldset className="start-auction-when">
          <legend>{t('startAuction.fields.start')}</legend>
          <label><input type="radio" name="startMode" value="now" checked={form.startMode === 'now'} onChange={update('startMode')} /> {t('startAuction.startNow')}</label>
          <label><input type="radio" name="startMode" value="later" checked={form.startMode === 'later'} onChange={update('startMode')} /> {t('startAuction.startLater')}</label>
        </fieldset>

        <div className="start-auction-grid">
          {form.startMode === 'later' && field('startsAt', 'starts_at',
            <input id="auction-startsAt" type="datetime-local" value={form.startsAt} onChange={update('startsAt', 'starts_at')} {...invalid('starts_at', 'startsAt')} />)}
          {field('endsAt', 'ends_at',
            <input id="auction-endsAt" type="datetime-local" value={form.endsAt} onChange={update('endsAt', 'ends_at')} {...invalid('ends_at', 'endsAt')} />,
            t('startAuction.durationHint', { min: rules.minDurationHours, max: rules.maxDurationDays }))}
        </div>

        {field('buyNowPrice', 'buy_now_price',
          <input id="auction-buyNowPrice" type="number" inputMode="decimal" min="1" step="any" value={form.buyNowPrice} onChange={update('buyNowPrice', 'buy_now_price')} placeholder={t('startAuction.optional')} {...invalid('buy_now_price', 'buyNowPrice')} />,
          t('startAuction.buyNowHint'))}

        {submitError && <p role="alert" className="start-auction-error">{submitError}</p>}
        <div className="start-auction-actions">
          <button type="submit" className="start-auction-primary" disabled={submitting}>
            {submitting ? t('auctions.pleaseWait') : t('startAuction.submit')}
          </button>
          <a href={listingHref} className="start-auction-secondary">{t('startAuction.cancel')}</a>
        </div>
      </form>
    </div>
  );
}
