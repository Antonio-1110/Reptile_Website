// Marketplace sort options: the API `ordering` each one sends (backend/post/views.py ListingOrderingFilter).
// Each ends in a tie-breaker so paging never repeats or skips listings with equal values.
export const LISTING_SORTS = {
  recommended: "recommended",
  newest: "-created_at,-id",
  priceLow: "price,-id",
  priceHigh: "-price,-id",
};

export const DEFAULT_LISTING_SORT = "recommended";
