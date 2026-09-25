import './AuctionCountdown.css';
import { useTranslation } from 'react-i18next';
import { ENDING_SOON_MS, formatDuration, getAuctionPhase } from '../../utils/auctionFormat';

// "3h 12m left" / "Starts in 18h 0m" / "Ended" pill. `now` comes from the page's useNow().
export default function AuctionCountdown({ auction, now, size = 'small' }) {
  const { t } = useTranslation();
  const phase = getAuctionPhase(auction, now);
  const msLeft = auction.endsAt.getTime() - now;

  let text;
  let tone = phase;
  if (phase === 'live') {
    text = t('auctions.countdown.left', { time: formatDuration(t, msLeft) });
    if (msLeft < ENDING_SOON_MS) tone = 'ending';
  } else if (phase === 'upcoming') {
    text = t('auctions.countdown.startsIn', { time: formatDuration(t, auction.startsAt.getTime() - now) });
  } else {
    text = t(`auctions.phase.${phase}`);
  }

  return (
    <span className={`auction-countdown auction-countdown--${tone} auction-countdown--${size}`}>
      {phase === 'live' && <span className="auction-countdown-dot" aria-hidden="true" />}
      {text}
    </span>
  );
}
