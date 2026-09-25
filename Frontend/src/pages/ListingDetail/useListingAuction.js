import { useCallback, useEffect, useRef, useState } from 'react';
import { isLoggedIn } from '../../api/authApi';
import { getAuctionBids, getLatestAuctionForListing, getMyOrderForAuction } from '../../api/auctionsApi';
import { getAuctionPhase } from '../../utils/auctionFormat';
import { toErrorState } from '../../utils/errorState';

// While an auction is running, reload it this often so other people's bids show up.
const REFRESH_MS = 15000;
const NO_BIDS = { results: [], count: 0 };

// The listing's latest (non-cancelled) auction, its bids and (after it ends) the viewer's order as
// buyer or seller, kept fresh while it runs. `loaded` is false until the first answer, so the page
// doesn't flash "for sale" before the auction.
export default function useListingAuction(listingId, now) {
  const [state, setState] = useState({ auction: null, bids: NO_BIDS, order: null, loaded: false, error: null });

  const refresh = useCallback(async () => {
    try {
      const auction = await getLatestAuctionForListing(listingId);
      const bids = auction ? await getAuctionBids(auction.id) : NO_BIDS;
      const over = auction && getAuctionPhase(auction, Date.now()) === 'ended';
      const order = over && isLoggedIn() ? await getMyOrderForAuction(auction.id) : null;
      setState({ auction, bids, order, loaded: true, error: null });
    } catch (error) {
      setState((current) => ({ ...current, loaded: true, error: toErrorState(error, 'auctions.detail.loadError') }));
    }
  }, [listingId]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const phase = state.auction ? getAuctionPhase(state.auction, now) : null;
  const isRunning = phase === 'live' || phase === 'upcoming';

  useEffect(() => {
    if (!isRunning) return undefined;
    const timer = setInterval(refresh, REFRESH_MS);
    return () => clearInterval(timer);
  }, [isRunning, refresh]);

  // Reload the moment the countdown reaches zero (or bidding opens), rather than on the next poll.
  const previousPhaseRef = useRef(phase);
  useEffect(() => {
    if (previousPhaseRef.current && phase && previousPhaseRef.current !== phase) refresh();
    previousPhaseRef.current = phase;
  }, [phase, refresh]);

  return { ...state, phase, refresh };
}
