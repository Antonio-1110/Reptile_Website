import { authFetch } from "./authApi";
import { getLocationKey } from "../constants/locations";

// Auction reads go through authFetch too: it only attaches a token when there is one, and signed-in
// viewers get their own deposit (`my_deposit`) and `is_seller` back.
const get = (path) => authFetch(path, { method: "GET" });
const post = (path, payload) => authFetch(path, {
  method: "POST",
  ...(payload ? { body: JSON.stringify(payload) } : {}),
});

function normalizeDeposit(deposit) {
  if (!deposit) return null;
  return { id: deposit.id, amount: deposit.amount, currency: deposit.currency, status: deposit.status };
}

function normalizePurchase(purchase) {
  if (!purchase) return null;
  return { id: purchase.id, amount: purchase.amount, currency: purchase.currency, status: purchase.status };
}

function normalizeAuction(item) {
  const listing = item.listing || {};
  return {
    id: item.id,
    status: item.status,
    sellerName: item.seller_name,
    isSeller: Boolean(item.is_seller),
    listing: {
      id: listing.id,
      category: listing.category,
      title: listing.title,
      image: listing.image || "",
      location: getLocationKey(listing.location) || listing.location,
      species: listing.species_name,
      sex: listing.sex,
      lifeStage: listing.life_stage,
      genes: listing.genes || [],
    },
    currency: item.currency,
    startingPrice: item.starting_price,
    minIncrement: item.min_increment,
    depositAmount: item.deposit_amount,
    startsAt: new Date(item.starts_at),
    endsAt: new Date(item.ends_at),
    bidCount: item.bid_count,
    currentPrice: item.current_price,
    minimumNextBid: item.minimum_next_bid,
    winningBidAmount: item.winning_bid_amount,
    // Buy now: the seller's optional fixed price, paid in full up front; the first payment wins.
    buyNowPrice: item.buy_now_price,
    buyNowAvailable: Boolean(item.buy_now_available),
    pendingBuyNowCount: item.pending_buy_now_count || 0,
    soldVia: item.sold_via, // "bid", "buy_now" or null
    soldPrice: item.sold_price,
    myDeposit: normalizeDeposit(item.my_deposit),
    myPurchase: normalizePurchase(item.my_purchase),
  };
}

function normalizeBid(bid) {
  return { id: bid.id, amount: bid.amount, createdAt: new Date(bid.created_at), isMine: bid.is_mine };
}

// The "Live" tab lists running and upcoming auctions, soonest to end first; "Ended" shows the most recent first.
const TAB_QUERIES = {
  live: { status: "active", ordering: "ends_at" },
  ended: { status: "ended", ordering: "-ends_at" },
};

export async function getAuctionsPage({ tab = "live", page = 1 } = {}) {
  const params = new URLSearchParams({ ...TAB_QUERIES[tab], page });
  const payload = await get(`/auctions/?${params}`);
  return {
    results: payload.results.map(normalizeAuction),
    count: payload.count,
    hasMore: Boolean(payload.next),
  };
}

export async function getAuction(id) {
  return normalizeAuction(await get(`/auctions/${id}/`));
}

export async function getAuctionBids(id, page = 1) {
  const payload = await get(`/auctions/${id}/bids/?page=${page}`);
  return { results: payload.results.map(normalizeBid), count: payload.count, hasMore: Boolean(payload.next) };
}

// A live-animal listing's most recent auction that wasn't cancelled (running, upcoming or ended),
// or null. A listing has at most one active auction, and it's always the newest.
export async function getLatestAuctionForListing(listingId) {
  const payload = await get(`/auctions/?live_animal_post=${listingId}&ordering=-created_at`);
  const latest = payload.results.find((item) => item.status !== "cancelled");
  return latest ? normalizeAuction(latest) : null;
}

// Returns the deposit plus `payment`: whatever the payment gateway needs the frontend to do next
// (e.g. {checkout_url}); empty when the deposit is already paid.
export async function payDeposit(id) {
  const result = await post(`/auctions/${id}/deposit/`);
  return { deposit: normalizeDeposit(result), payment: result.payment || {} };
}

export async function placeBid(id, amount) {
  return normalizeBid(await post(`/auctions/${id}/bids/`, { amount: String(amount) }));
}

// Pay the buy-now price in full. Returns the purchase, `payment` (what the gateway needs the frontend
// to do next, e.g. {checkout_url}) and how many other buyers are paying at the same moment.
export async function startBuyNow(id) {
  const result = await post(`/auctions/${id}/buy-now/`);
  return { purchase: normalizePurchase(result), payment: result.payment || {}, competingBuyers: result.competing_buyers || 0 };
}

// --- Orders: what happens after a sale (pay the rest, hand over, confirm). Buyer and seller only. ---

const toDate = (value) => (value ? new Date(value) : null);

function normalizeOrder(item) {
  return {
    id: item.id,
    role: item.role, // "buyer" or "seller": which side the viewer is on
    source: item.source, // "bid", "buy_now" or "runner_up"
    status: item.status,
    price: item.price,
    currency: item.currency,
    depositAmount: item.deposit_amount,
    balance: item.balance,
    balanceStatus: item.balance_status,
    payout: item.payout,
    paymentDueAt: toDate(item.payment_due_at),
    handoverDueAt: toDate(item.handover_due_at),
    confirmDueAt: toDate(item.confirm_due_at),
    handoverNote: item.handover_note,
    problemReport: item.problem_report,
    runnerUpDecision: item.runner_up_decision,
    runnerUpAmount: item.runner_up_amount,
    // The other side's contact details, once the order has got far enough (null before that).
    counterpart: item.counterpart,
  };
}

// The viewer's latest order for an auction (as buyer or seller), or null.
export async function getMyOrderForAuction(auctionId) {
  const payload = await get(`/auctions/orders/?auction=${auctionId}`);
  return payload.results.length ? normalizeOrder(payload.results[0]) : null;
}

const orderAction = (name) => async (id, payload) => normalizeOrder(await post(`/auctions/orders/${id}/${name}/`, payload));
export const payOrder = orderAction("pay");
export const markHandedOver = (id, note) => orderAction("handed-over")(id, { note });
export const confirmReceived = orderAction("confirm");
export const reportProblem = (id, text) => orderAction("report-problem")(id, { text });
export const decideRunnerUp = (id, offer) => orderAction("runner-up")(id, { offer });
export const declineOffer = orderAction("decline");

export async function cancelAuction(id) {
  return normalizeAuction(await post(`/auctions/${id}/cancel/`));
}
