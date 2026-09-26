import './SellerReviews.css';
import { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { deleteSellerReview, getSellerReviews, isLoggedIn, saveSellerReview } from '../api/listingsApi';
import { formatDateTime } from '../utils/auctionFormat';
import { errorText, toErrorState } from '../utils/errorState';

const STARS = [1, 2, 3, 4, 5];

function Stars({ rating }) {
  return <span className="review-stars" aria-hidden="true">{'★'.repeat(rating)}{'☆'.repeat(5 - rating)}</span>;
}

// Reviews on a seller's page, and the form for buyers who may leave one (the API decides who can:
// someone who contacted the seller about a listing, or bought from them at auction).
export default function SellerReviews({ profile, onRatingChanged }) {
  const { t, i18n } = useTranslation();
  const [feed, setFeed] = useState({ reviews: [], count: 0, nextPage: 1, loading: true, error: null });
  const [draft, setDraft] = useState({ rating: profile.myReview?.rating || 0, comment: profile.myReview?.comment || '' });
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState('');
  const [savedMessage, setSavedMessage] = useState('');

  const load = useCallback((page) => {
    setFeed((current) => ({ ...current, loading: true, error: null }));
    getSellerReviews(profile.id, page)
      .then(({ results, count, hasMore }) => setFeed((current) => ({
        reviews: page === 1 ? results : [...current.reviews, ...results],
        count,
        nextPage: hasMore ? page + 1 : null,
        loading: false,
        error: null,
      })))
      .catch((error) => setFeed((current) => ({ ...current, loading: false, error: toErrorState(error, 'reviews.loadError') })));
  }, [profile.id]);

  useEffect(() => {
    load(1);
  }, [load]);

  const afterChange = (message) => {
    setSavedMessage(message);
    load(1);
    onRatingChanged();
  };

  const submit = async (event) => {
    event.preventDefault();
    if (!draft.rating) {
      setFormError(t('reviews.pickRating'));
      return;
    }
    setSaving(true);
    setFormError('');
    setSavedMessage('');
    try {
      await saveSellerReview(profile.id, draft.rating, draft.comment.trim());
      afterChange(t('reviews.saved'));
    } catch (error) {
      setFormError(error.message);
    } finally {
      setSaving(false);
    }
  };

  const remove = async () => {
    setSaving(true);
    setFormError('');
    try {
      await deleteSellerReview(profile.id);
      setDraft({ rating: 0, comment: '' });
      afterChange(t('reviews.deleted'));
    } catch (error) {
      setFormError(error.message);
    } finally {
      setSaving(false);
    }
  };

  let formArea;
  if (profile.canReview) {
    formArea = (
      <form className="review-form" onSubmit={submit}>
        <fieldset className="review-form-stars">
          <legend>{profile.myReview ? t('reviews.editHeading') : t('reviews.writeHeading')}</legend>
          {STARS.map((value) => (
            <label key={value} className={`review-star${value <= draft.rating ? ' is-on' : ''}`}>
              <input
                type="radio"
                name="rating"
                value={value}
                checked={draft.rating === value}
                onChange={() => setDraft((current) => ({ ...current, rating: value }))}
              />
              <span aria-hidden="true">★</span>
              <span className="review-sr">{t('reviews.stars', { count: value })}</span>
            </label>
          ))}
        </fieldset>
        <label className="review-form-comment">
          <span>{t('reviews.comment')}</span>
          <textarea
            value={draft.comment}
            maxLength={1000}
            onChange={(event) => setDraft((current) => ({ ...current, comment: event.target.value }))}
            placeholder={t('reviews.commentPlaceholder')}
          />
        </label>
        {formError && <p role="alert" className="review-error">{formError}</p>}
        {savedMessage && <p role="status" className="review-saved">{savedMessage}</p>}
        <div className="review-form-actions">
          <button type="submit" className="review-submit" disabled={saving}>
            {saving ? t('auctions.pleaseWait') : profile.myReview ? t('reviews.update') : t('reviews.submit')}
          </button>
          {profile.myReview && (
            <button type="button" className="review-delete" disabled={saving} onClick={remove}>{t('reviews.delete')}</button>
          )}
        </div>
      </form>
    );
  } else if (!isLoggedIn()) {
    const next = encodeURIComponent(window.location.pathname);
    formArea = <p className="review-hint"><a href={`/signin?next=${next}`}>{t('reviews.signIn')}</a></p>;
  } else {
    formArea = <p className="review-hint">{t('reviews.notEligible')}</p>;
  }

  return (
    <section className="seller-reviews" aria-labelledby="seller-reviews-heading">
      <h2 id="seller-reviews-heading">{t('reviews.heading', { count: feed.count })}</h2>
      {formArea}
      {feed.error && <p role="alert" className="review-error">{errorText(t, feed.error)}</p>}
      {!feed.loading && !feed.error && feed.reviews.length === 0 && <p className="review-hint">{t('reviews.empty')}</p>}
      <ul className="review-list">
        {feed.reviews.map((review) => (
          <li key={review.id} className="review-item">
            <div className="review-item-top">
              <Stars rating={review.rating} />
              <span className="review-sr">{t('reviews.stars', { count: review.rating })}</span>
              <strong>{review.reviewer}</strong>
              {review.isMine && <span className="review-mine">{t('reviews.yours')}</span>}
              <time dateTime={review.createdAt.toISOString()}>{formatDateTime(review.createdAt, i18n.resolvedLanguage)}</time>
            </div>
            {review.comment && <p>{review.comment}</p>}
          </li>
        ))}
      </ul>
      {feed.nextPage && feed.reviews.length > 0 && (
        <button type="button" className="review-more" disabled={feed.loading} onClick={() => load(feed.nextPage)}>{t('reviews.showMore')}</button>
      )}
    </section>
  );
}
