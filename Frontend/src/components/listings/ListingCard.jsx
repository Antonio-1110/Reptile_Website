import React from 'react';
import { useTranslation } from 'react-i18next';
import './ListingCard.css';
import { getLocationLabel } from '../../constants/locations';
import { getSexKey } from '../../api/listingsApi';

export default function ListingCard({ animal }) {
  const { t } = useTranslation();
  const locationName = getLocationLabel(t, animal.location);

  return (
    <a href={`/posts/${animal.id}`} className="card-container">
      <img
        src={animal.image}
        alt={animal.title}
        className="card-image"
        loading="lazy"
        decoding="async"
      />
      
      <div className="card-content">
        <div className="card-header">
          <h3 className="card-title">{animal.title}</h3>
          <span className="card-sex">
            {t(`createListing.sex.${getSexKey(animal.sex)}`)}
          </span>
        </div>

        {/* Genetic Badges */}
        <div className="card-genes" title={animal.genes.join(' / ') || undefined}>
          {animal.genes.map((gene, idx) => (
            <span key={idx} className="card-gene-badge">
              {gene}
            </span>
          ))}
        </div>

        <div className="card-footer">
          <p className="card-location">{t('filters.location')}: {locationName}</p>
          <span className="card-price">${animal.price}</span>
        </div>

        <div className="card-seller-row">
          <span>{t('listings.seller')}</span>
          <a
            href={`/marketplace?search=${encodeURIComponent(animal.sellerTag || animal.seller)}`}
            onClick={(event) => event.stopPropagation()}
          >
            {animal.sellerTag || animal.seller}
          </a>
        </div>
      </div>
    </a>
  );
}