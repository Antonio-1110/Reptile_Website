import "./MarketplacePage.css";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import FilterSidebar from "../components/filters/FilterSidebar";
import EndOfResultsCard from "../components/listings/EndOfResultsCard";
import ListingCard from "../components/listings/ListingCard";
import ListingGrid from "../components/listings/ListingGrid";
import { createSavedSearch, getListingsPage, isLoggedIn, listingQueryString } from "../api/listingsApi";
import useDebouncedValue from "../hooks/useDebouncedValue";
import { readMarketplaceCategory, withMarketplaceCategory } from "../utils/marketplaceSearch";

const initialFilters = {
  minPrice: "", maxPrice: "", minSize: "", maxSize: "",
  minPostedDays: "", maxPostedDays: "", sex: [],
  locations: [], includeLocations: true, lifeStages: [], includeLifeStages: true,
  minAgeYears: "", maxAgeYears: "", minWeight: "", maxWeight: "",
  diets: [], includeDiets: true, shippingMethods: [], includeShipping: true,
  equipmentTypes: [], conditions: [],
};

// Start fetching the next page while the user is still this far above the end of the grid.
const PREFETCH_MARGIN = "800px";

// loadingPage / failedPage: which page is in flight or last failed (null when none).
const emptyFeed = { listings: [], count: 0, nextPage: 1, loadingPage: 1, failedPage: null };

export default function MarketplacePage({ searchTerm = "", searchTags = [], onClearSearch }) {
  const { t } = useTranslation();
  // "live_animal" or "equipment": which kind of listing the whole page shows.
  const [category, setCategory] = useState(readMarketplaceCategory);
  const [filters, setFilters] = useState(initialFilters);
  const debouncedFilters = useDebouncedValue(filters, 300);
  const [feed, setFeed] = useState(emptyFeed);
  const queryIdRef = useRef(0);
  const sentinelRef = useRef(null);

  const query = useMemo(
    () => ({ category, search: searchTerm, tags: searchTags, filters: debouncedFilters }),
    [category, searchTerm, searchTags, debouncedFilters],
  );

  // Loads one page for the current query. Responses for an outdated query are dropped, so changing a
  // filter mid-request can't mix old results into the new list.
  const fetchPage = useCallback((page) => {
    const queryId = queryIdRef.current;
    setFeed((current) => ({ ...current, loadingPage: page, failedPage: null }));
    getListingsPage({ ...query, page })
      .then(({ results, count, hasMore }) => {
        if (queryId !== queryIdRef.current) return;
        setFeed((current) => ({
          listings: page === 1 ? results : [...current.listings, ...results],
          count,
          nextPage: hasMore ? page + 1 : null,
          loadingPage: null,
          failedPage: null,
        }));
      })
      .catch(() => {
        if (queryId !== queryIdRef.current) return;
        setFeed((current) => ({ ...current, loadingPage: null, failedPage: page }));
      });
  }, [query]);

  // New search or filters: start over from page 1 (the previous results stay visible until it arrives).
  useEffect(() => {
    queryIdRef.current += 1;
    fetchPage(1);
  }, [fetchPage]);

  // Infinite scroll: when the sentinel below the grid comes near the viewport, fetch the next page.
  // The observer is rebuilt after every load, so a short page on a tall screen keeps loading until
  // the viewport is filled.
  useEffect(() => {
    const sentinel = sentinelRef.current;
    if (!sentinel || feed.loadingPage || feed.failedPage || feed.nextPage === null) return undefined;
    const observer = new IntersectionObserver(
      ([entry]) => entry.isIntersecting && fetchPage(feed.nextPage),
      { rootMargin: `0px 0px ${PREFETCH_MARGIN} 0px` },
    );
    observer.observe(sentinel);
    return () => observer.disconnect();
  }, [feed.loadingPage, feed.failedPage, feed.nextPage, fetchPage]);

  const hasListings = feed.listings.length > 0;
  const isFirstLoad = feed.loadingPage === 1 && !hasListings;
  const isRefreshing = feed.loadingPage === 1 && hasListings;
  const isLoadingMore = feed.loadingPage > 1;
  const reachedEnd = !feed.loadingPage && !feed.failedPage && feed.nextPage === null;
  const errorMessage = feed.failedPage && t(feed.failedPage === 1 ? "listings.loadError" : "listings.loadMoreError");
  // "Save this search": null, "saving", "saved" or an error message.
  const [saveState, setSaveState] = useState(null);
  useEffect(() => setSaveState(null), [query]);
  const saveSearch = async () => {
    setSaveState("saving");
    try {
      await createSavedSearch(listingQueryString(query), searchTerm.trim());
      setSaveState("saved");
    } catch (error) {
      setSaveState(error.message);
    }
  };

  const changeCategory = (value) => {
    setCategory(value);
    window.history.replaceState(null, "", withMarketplaceCategory(value));
  };
  const clearFilters = () => {
    setFilters(initialFilters);
    if (searchTerm || searchTags.length) onClearSearch?.();
  };

  return (
    <div className="marketplace-page">
      <div className="marketplace-layout">
        <FilterSidebar category={category} onCategoryChange={changeCategory} filters={filters} setFilters={setFilters} />
        <main className="marketplace-main">
          <div className="marketplace-results" aria-busy={Boolean(feed.loadingPage)}>
            <div className="marketplace-heading-row">
              <h1 className="marketplace-heading">{t("listings.available", { count: feed.count })}</h1>
              {/* Saved searches (and their email alerts) cover live animals only. */}
              {isLoggedIn() && category === "live_animal" && (
                <div className="marketplace-save-search">
                  {saveState === "saved" ? (
                    <p role="status">
                      {t("savedSearches.savedNote")} <a href="/saved-searches">{t("savedSearches.manage")}</a>
                    </p>
                  ) : (
                    <button type="button" onClick={saveSearch} disabled={saveState === "saving"}>
                      🔔 {t("savedSearches.save")}
                    </button>
                  )}
                  {saveState && !["saving", "saved"].includes(saveState) && <p role="alert">{saveState}</p>}
                </div>
              )}
            </div>
            {isFirstLoad && <p className="marketplace-status">{t("listings.loading")}</p>}

            {(hasListings || reachedEnd) && (
              <div className={`marketplace-feed${isRefreshing ? " is-refreshing" : ""}`}>
                <ListingGrid>
                  {feed.listings.map((listing) => <ListingCard key={`${listing.kind || "animal"}-${listing.id}`} animal={listing} />)}
                  {reachedEnd && <EndOfResultsCard empty={feed.count === 0} onClearFilters={clearFilters} />}
                </ListingGrid>
              </div>
            )}

            <div ref={sentinelRef} className="marketplace-sentinel" aria-hidden="true" />
            {isLoadingMore && (
              <p className="marketplace-status marketplace-status--more" role="status">{t("listings.loadingMore")}</p>
            )}
            {errorMessage && (
              <p className="marketplace-status marketplace-status--more" role="alert">
                {errorMessage}{" "}
                <button type="button" className="marketplace-retry" onClick={() => fetchPage(feed.failedPage)}>
                  {t("listings.retry")}
                </button>
              </p>
            )}
          </div>
        </main>
      </div>
    </div>
  );
}
