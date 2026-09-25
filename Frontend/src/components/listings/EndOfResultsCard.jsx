import './EndOfResultsCard.css';
import { useTranslation } from 'react-i18next';

// Easter egg "listing" that closes out the marketplace feed. With `empty` it stands in for the
// whole grid when nothing matches; otherwise it marks the end of the results.
export default function EndOfResultsCard({ empty = false, onClearFilters }) {
  const { t } = useTranslation();
  const variant = empty ? 'empty' : 'end';
  const action = empty
    ? onClearFilters && { label: t('listings.endCard.clearFilters'), run: onClearFilters }
    : { label: t('listings.endCard.backToTop'), run: () => window.scrollTo({ top: 0, behavior: 'smooth' }) };

  return (
    <article className={`end-card end-card--${variant}`}>
      <div className="end-card-scene" aria-hidden="true">
        <span className="end-card-moon">☾</span>
        <span className="end-card-gecko">🦎</span>
        <span className="end-card-zzz">
          <span>z</span><span>z</span><span>z</span>
        </span>
        <span className="end-card-substrate" />
      </div>

      <div className="end-card-content">
        <div className="end-card-header">
          <h3 className="end-card-title">{t(`listings.endCard.${variant}.title`)}</h3>
          <span className="end-card-sex" title={t('listings.endCard.sexHint')}>0.0.1</span>
        </div>

        <p className="end-card-caption">{t(`listings.endCard.${variant}.caption`)}</p>

        <div className="end-card-genes">
          <span className="end-card-gene">{t(`listings.endCard.${variant}.geneA`)}</span>
          <span className="end-card-gene">{t(`listings.endCard.${variant}.geneB`)}</span>
        </div>

        <div className="end-card-footer">
          <p className="end-card-location">{t('filters.location')}: {t('listings.endCard.location')}</p>
          <span className="end-card-price">{t('listings.endCard.price')}</span>
        </div>

        {action && (
          <button type="button" className="end-card-action" onClick={action.run}>
            {action.label}
          </button>
        )}
      </div>
    </article>
  );
}
