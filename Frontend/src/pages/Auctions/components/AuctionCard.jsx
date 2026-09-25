import './AuctionCard.css';
import { useTranslation } from 'react-i18next';
import AuctionCountdown from '../../../components/auctions/AuctionCountdown';
import { getSexKey } from '../../../api/listingsApi';
import { getSpeciesLabel } from '../../../constants/species';
import { formatMoney, getAuctionPhase, getHeadlinePrice } from '../../../utils/auctionFormat';

const MAX_GENES = 3;

export default function AuctionCard({ auction, now }) {
  const { t, i18n } = useTranslation();
  const { listing } = auction;
  const phase = getAuctionPhase(auction, now);
  const price = getHeadlinePrice(auction, phase);
  const extraGenes = listing.genes.length - MAX_GENES;
  const money = (amount) => formatMoney(amount, auction.currency, i18n.resolvedLanguage);
  const showBuyNow = (phase === 'live' || phase === 'upcoming') && auction.buyNowAvailable;
  // The auction is shown on the animal's own page; /auctions/:id covers listings without one.
  const href = listing.category === 'live_animal' ? `/posts/${listing.id}` : `/auctions/${auction.id}`;

  return (
    <a href={href} className="auction-card">
      <div className="auction-card-media">
        {listing.image
          ? <img src={listing.image} alt={listing.title} className="auction-card-image" loading="lazy" decoding="async" />
          : <div className="auction-card-image auction-card-image--empty" aria-hidden="true">🦎</div>}
        <div className="auction-card-countdown">
          <AuctionCountdown auction={auction} now={now} />
        </div>
      </div>

      <div className="auction-card-content">
        <h3 className="auction-card-title">{listing.title}</h3>
        <p className="auction-card-subtitle">
          {listing.species ? getSpeciesLabel(t, listing.species) : t('auctions.equipment')}
          {listing.sex && <> · {t(`createListing.sex.${getSexKey(listing.sex)}`)}</>}
        </p>

        <div className="auction-card-genes">
          {listing.genes.slice(0, MAX_GENES).map((gene) => (
            <span key={gene} className="auction-card-gene">{gene}</span>
          ))}
          {extraGenes > 0 && <span className="auction-card-gene auction-card-gene--more">+{extraGenes}</span>}
        </div>

        <div className="auction-card-footer">
          <div>
            <p className="auction-card-price-label">{t(price.labelKey)}</p>
            <p className="auction-card-price">{money(price.amount)}</p>
          </div>
          <p className="auction-card-bids">{t('auctions.bidCount', { count: auction.bidCount })}</p>
        </div>
        {showBuyNow && <p className="auction-card-buy-now">{t('auctions.card.buyNow', { amount: money(auction.buyNowPrice) })}</p>}

        <p className="auction-card-seller">
          <span>{t('listings.seller')}</span>
          <strong>{auction.sellerName}</strong>
        </p>
      </div>
    </a>
  );
}
