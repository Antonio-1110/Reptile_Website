// UI language → locale for Intl formatting (matches the codes sent to the backend in api/http.js).
const INTL_LOCALES = { en: "en", zh: "zh-Hant-TW" };

export function intlLocale(language) {
  return INTL_LOCALES[language] || "en";
}

// "5000.00" + "TWD" → "NT$5,000" (en) / "$5,000" (zh). Cents only when there are any.
export function formatMoney(amount, currency, language) {
  if (amount == null || amount === "") return "";
  const value = Number(amount);
  return new Intl.NumberFormat(intlLocale(language), {
    style: "currency",
    currency: currency || "TWD",
    minimumFractionDigits: Number.isInteger(value) ? 0 : 2,
    maximumFractionDigits: 2,
  }).format(value);
}

export function formatDateTime(date, language) {
  return new Intl.DateTimeFormat(intlLocale(language), { dateStyle: "medium", timeStyle: "short" }).format(date);
}

// "3 minutes ago" etc., for bid history.
export function formatRelativeTime(date, now, language) {
  const seconds = Math.round((date.getTime() - now) / 1000);
  const units = [["day", 86400], ["hour", 3600], ["minute", 60]];
  const format = new Intl.RelativeTimeFormat(intlLocale(language), { numeric: "auto" });
  for (const [unit, size] of units) {
    if (Math.abs(seconds) >= size) return format.format(Math.trunc(seconds / size), unit);
  }
  return format.format(0, "minute");
}

// Where an auction is at `now`. The server's `status` only changes when close_auctions runs, so an
// active auction past its end time is already shown as ended.
export function getAuctionPhase(auction, now) {
  if (auction.status === "cancelled") return "cancelled";
  if (auction.status === "ended" || now >= auction.endsAt.getTime()) return "ended";
  if (now < auction.startsAt.getTime()) return "upcoming";
  return "live";
}

// Under this much time left, the countdown is highlighted.
export const ENDING_SOON_MS = 60 * 60 * 1000;

// Milliseconds → a short translated duration: "2d 4h", "3h 12m" or "4m 05s".
export function formatDuration(t, ms) {
  const totalSeconds = Math.max(0, Math.floor(ms / 1000));
  const d = Math.floor(totalSeconds / 86400);
  const h = Math.floor((totalSeconds % 86400) / 3600);
  const m = Math.floor((totalSeconds % 3600) / 60);
  const s = String(totalSeconds % 60).padStart(2, "0");
  if (d > 0) return t("auctions.duration.days", { d, h });
  if (h > 0) return t("auctions.duration.hours", { h, m });
  return t("auctions.duration.minutes", { m, s });
}

// The headline price for an auction and which label goes with it.
export function getHeadlinePrice(auction, phase) {
  if (auction.saleFellThrough) return { labelKey: "auctions.price.saleFellThrough", amount: auction.soldPrice };
  if (auction.soldVia === "buy_now") return { labelKey: "auctions.price.boughtNow", amount: auction.soldPrice };
  // Before close_auctions runs, an auction past its end has no winning_bid yet; its top bid is the winner.
  const topBid = phase === "ended" ? auction.winningBidAmount || auction.currentPrice : auction.currentPrice;
  if (!topBid) return { labelKey: "auctions.price.startingBid", amount: auction.startingPrice };
  return { labelKey: phase === "ended" ? "auctions.price.winningBid" : "auctions.price.currentBid", amount: topBid };
}
