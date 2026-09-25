import './AuctionRedirectPage.css';
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { getAuction } from '../../api/auctionsApi';

// Old /auctions/:id links: an auction lives on its animal's page, so send the visitor there.
export default function AuctionRedirectPage({ auctionId }) {
  const { t } = useTranslation();
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    getAuction(auctionId)
      .then((auction) => {
        // Equipment has no detail page yet, so only live-animal auctions have somewhere to go.
        if (auction.listing.category === 'live_animal') window.location.replace(`/posts/${auction.listing.id}`);
        else setFailed(true);
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
