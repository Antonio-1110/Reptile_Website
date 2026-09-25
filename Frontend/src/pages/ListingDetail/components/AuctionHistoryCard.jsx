import './AuctionHistoryCard.css';
import { useTranslation } from 'react-i18next';
import { formatDateTime, formatMoney, formatRelativeTime } from '../../../utils/auctionFormat';

// Bid history (highest first; bidders stay anonymous apart from "You") and the auction's terms.
export default function AuctionHistoryCard({ auction, bids, phase, now, className = '' }) {
  const { t, i18n } = useTranslation();
  const language = i18n.resolvedLanguage;
  const money = (amount) => formatMoney(amount, auction.currency, language);
  const hiddenBidCount = bids.count - bids.results.length;
  const terms = [
    ['startingPrice', money(auction.startingPrice)],
    ['increment', money(auction.minIncrement)],
    ['startsAt', formatDateTime(auction.startsAt, language)],
    ['endsAt', formatDateTime(auction.endsAt, language)],
  ];

  return (
    <section className={`auction-history ${className}`}>
      <h2>{t('auctions.detail.history')}</h2>
      {bids.results.length === 0 ? (
        <p className="auction-history-muted">
          {t(phase === 'upcoming' ? 'auctions.detail.noBidsYetUpcoming' : 'auctions.detail.noBidsYet', {
            amount: money(auction.startingPrice),
          })}
        </p>
      ) : (
        <ol className="auction-history-bids">
          {bids.results.map((bid, index) => (
            <li key={bid.id} className={`auction-history-bid${index === 0 ? ' is-top' : ''}`}>
              <span className="auction-history-amount">{money(bid.amount)}</span>
              <span className="auction-history-tags">
                {/* After a buy-now sale no bid won, so the top bid gets no tag. */}
                {index === 0 && auction.soldVia !== 'buy_now' && (
                  <span className="auction-history-tag auction-history-tag--top">
                    {t(phase === 'ended' ? 'auctions.detail.winningTag' : 'auctions.detail.leadingTag')}
                  </span>
                )}
                {bid.isMine && <span className="auction-history-tag">{t('auctions.detail.youTag')}</span>}
              </span>
              <time className="auction-history-time" dateTime={bid.createdAt.toISOString()} title={formatDateTime(bid.createdAt, language)}>
                {formatRelativeTime(bid.createdAt, now, language)}
              </time>
            </li>
          ))}
        </ol>
      )}
      {hiddenBidCount > 0 && <p className="auction-history-muted">{t('auctions.detail.moreBids', { count: hiddenBidCount })}</p>}

      <h3>{t('auctions.detail.details')}</h3>
      <dl className="auction-history-terms">
        {terms.map(([key, value]) => (
          <div key={key}>
            <dt>{t(`auctions.detail.facts.${key}`)}</dt>
            <dd>{value}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}
