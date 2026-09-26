import './AuctionRedirectPage.css';
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { getAuction } from '../../api/auctionsApi';
import { listingPagePath } from '../../api/listingsApi';

// Old /auctions/:id links: an auction lives on its listing's page, so send the visitor there.
export default function AuctionRedirectPage({ auctionId }) {
  const { t } = useTranslation();
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    getAuction(auctionId)
      .then((auction) => {
        window.location.replace(listingPagePath(auction.listing.id, auction.listing.category));
      })
      .catch(() => setFailed(true));
  }, [auctionId]);

  if (!failed) return <p className="auction-redirect">{t('auctions.detail.loading')}</p>;
  return (
    <div className="auction-redirect">
      <h1>{t('auctions.detail.notFound')}</h1>
      <a href="/auctions">{t('auctions.detail.back')}</a>
    </div>
  );
}
