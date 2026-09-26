import React from 'react';
import { useTranslation } from 'react-i18next';
import './ListingCard.css';
import { getLocationLabel } from '../../constants/locations';
import { getSexKey, listingPagePath, sellerPagePath } from '../../api/listingsApi';
import FavoriteButton from './FavoriteButton';
import { Link } from 'react-router';

// Draws a live animal or (animal.kind === "equipment") a piece of equipment.
export default function ListingCard({ animal }) {
  const { t } = useTranslation();
  const locationName = getLocationLabel(t, animal.location);
  const isEquipment = animal.kind === 'equipment';
  const detailHref = listingPagePath(animal.id, isEquipment ? 'equipment' : 'live_animal');
  const badges = isEquipment ? [t(`createListing.equipment.types.${animal.equipmentCategory}`)] : animal.genes;

  return (
    // Not a link itself: the seller link inside would be an <a> within an <a>, which is invalid HTML.
    // The title link stretches over the whole card instead (see .card-title-link::after).
    <article className="card-container">
      <div className="card-media">
        {animal.image ? (
          <img
            src={animal.image}
            alt={animal.title}
            className="card-image"
            loading="lazy"
            decoding="async"
          />
        ) : (
          <div className="card-image card-image--empty" aria-hidden="true">{isEquipment ? '🧰' : '🦎'}</div>
        )}
        {animal.status && animal.status !== 'available' && (
          <span className={`card-status card-status--${animal.status}`}>{t(`listingStatus.${animal.status}`)}</span>
        )}
        <FavoriteButton
          listingId={animal.id}
          category={isEquipment ? 'equipment' : 'live_animal'}
          initial={animal.isFavorite}
          className="card-favorite"
        />
      </div>

      <div className="card-content">
        <div className="card-header">
          <h3 className="card-title">
            <Link to={detailHref} className="card-title-link">{animal.title}</Link>
          </h3>
          <span className="card-sex">
            {isEquipment
              ? t(`createListing.equipment.conditions.${animal.condition}`)
              : t(`createListing.sex.${getSexKey(animal.sex)}`)}
          </span>
        </div>

        {/* Genes for animals, the type for equipment */}
        <div className="card-genes" title={badges.join(' / ') || undefined}>
          {badges.map((gene, idx) => (
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
          <Link to={sellerPagePath(animal.sellerId)}>
            {animal.sellerTag || animal.seller}
          </Link>
        </div>
      </div>
    </article>
  );
}