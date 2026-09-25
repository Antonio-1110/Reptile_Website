import "./MarketplacePage.css";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import FilterSidebar from "../components/filters/FilterSidebar";
import EndOfResultsCard from "../components/listings/EndOfResultsCard";
import ListingCard from "../components/listings/ListingCard";
import ListingCardSkeleton from "../components/listings/ListingCardSkeleton";
import ListingGrid from "../components/listings/ListingGrid";
import { getListingsPage } from "../api/listingsApi";
import useDebouncedValue from "../hooks/useDebouncedValue";

const initialFilters = {
  minPrice: "", maxPrice: "", minSize: "", maxSize: "",
  minPostedDays: "", maxPostedDays: "", sex: [],
  locations: [], includeLocations: true, lifeStages: [], includeLifeStages: true,
  minAgeYears: "", maxAgeYears: "", minWeight: "", maxWeight: "",
  diets: [], includeDiets: true, shippingMethods: [], includeShipping: true,
};

// Start fetching the next page while the user is still this far above the end of the grid.
const PREFETCH_MARGIN = "800px";

// loadingPage / failedPage: which page is in flight or last failed (null when none).
const emptyFeed = { listings: [], count: 0, nextPage: 1, loadingPage: 1, failedPage: null };

export default function MarketplacePage({ searchTerm = "", searchTags = [], onClearSearch }) {
  const { t } = useTranslation();
  const [filters, setFilters] = useState(initialFilters);
  const debouncedFilters = useDebouncedValue(filters, 300);
  const [feed, setFeed] = useState(emptyFeed);
  const queryIdRef = useRef(0);
  const sentinelRef = useRef(null);

  const query = useMemo(
    () => ({ search: searchTerm, tags: searchTags, filters: debouncedFilters }),
    [searchTerm, searchTags, debouncedFilters],
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
  const clearFilters = () => {
    setFilters(initialFilters);
    if (searchTerm || searchTags.length) onClearSearch?.();
  };

  return (
    <div className="marketplace-page">
      <div className="marketplace-layout">
        <FilterSidebar filters={filters} setFilters={setFilters} />
        <main className="marketplace-main">
          <div className="marketplace-results" aria-busy={Boolean(feed.loadingPage)}>
            {/* The count is only known once a page has loaded; "(0)" while loading would read as "no results". */}
            <h1 className="marketplace-heading">
              {hasListings || reachedEnd ? t("listings.available", { count: feed.count }) : t("listings.heading")}
            </h1>
            {isFirstLoad && (
              <>
                <p className="sr-only" role="status">{t("listings.loading")}</p>
                <ListingGrid>
                  {Array.from({ length: 6 }, (_, index) => <ListingCardSkeleton key={index} />)}
                </ListingGrid>
              </>
            )}

            {(hasListings || reachedEnd) && (
              <div className={`marketplace-feed${isRefreshing ? " is-refreshing" : ""}`}>
                <ListingGrid>
                  {feed.listings.map((animal) => <ListingCard key={animal.id} animal={animal} />)}
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
