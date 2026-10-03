import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import ListingCard from '../../../components/listings/ListingCard';
import ListingGrid from '../../../components/listings/ListingGrid';
import { getSimilarListings } from '../../../api/listingsApi';
import './SimilarListings.css';

// Other listings like this one, under the listing. It's a suggestion, not part of the listing, so it
// loads after the page and simply stays away when there are none or the request fails.
export default function SimilarListings({ listingId, category }) {
  const { t } = useTranslation();
  const [state, setState] = useState({ key: null, listings: [] });
  const key = `${category}-${listingId}`;

  useEffect(() => {
    let cancelled = false;
    getSimilarListings(listingId, category)
      .then((listings) => !cancelled && setState({ key, listings }))
      .catch(() => !cancelled && setState({ key, listings: [] }));
    return () => { cancelled = true; };
  }, [listingId, category, key]);

  // Listings from the previous page stay out while the next listing's suggestions load.
  const listings = state.key === key ? state.listings : [];
  if (!listings.length) return null;
  return (
    <section className="similar-listings" aria-labelledby="similar-listings-title">
      <h2 id="similar-listings-title">{t('similarListings.title')}</h2>
      <ListingGrid>
        {listings.map((listing) => <ListingCard key={`${listing.kind || 'animal'}-${listing.id}`} animal={listing} />)}
      </ListingGrid>
    </section>
  );
}
