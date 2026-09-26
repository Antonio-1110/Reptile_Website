import React, { useMemo } from "react";
import { Navigate, Route, Routes, useLocation, useNavigate, useParams, useSearchParams } from "react-router";
import Header from "./components/layout/Header";
import HomePage from "./pages/HomePage";
import MarketplacePage from "./pages/MarketplacePage";
import ListingEditorPage from "./pages/ListingEditor/ListingEditorPage";
import AccountSettingsPage from "./pages/AccountSettingsPage";
import ListingDetailPage from "./pages/ListingDetail/ListingDetailPage";
import MyListingsPage from "./pages/MyListingsPage";
import MyOrdersPage from "./pages/MyOrdersPage";
import SellerProfilePage from "./pages/SellerProfilePage";
import SavedSearchesPage from "./pages/SavedSearchesPage";
import SavedListingsPage from "./pages/SavedListingsPage";
import AuctionsPage from "./pages/Auctions/AuctionsPage";
import StartAuctionPage from "./pages/Auctions/StartAuctionPage";
import AuctionRedirectPage from "./pages/Auctions/AuctionRedirectPage";
import SignInPage from "./pages/SignInPage";
import UpgradePage from "./pages/UpgradePage";
import { isLoggedIn } from "./api/authApi";
import { buildMarketplaceUrl, readMarketplaceCategory, readMarketplaceSearch } from "./utils/marketplaceSearch";

// Sends a signed-out visitor to sign in, then back to the page (query included) they asked for.
// The backend enforces auth regardless; this just avoids showing a form they can't submit.
function RequireSignIn({ children }) {
  const location = useLocation();
  if (isLoggedIn()) return children;
  const next = location.pathname + location.search;
  return <Navigate to={`/signin?next=${encodeURIComponent(next)}`} replace />;
}

// Pages that read their query string only when they mount (the editor, the auction form, sign-in)
// start afresh when a link changes it, e.g. "Post listing" clicked while editing another listing.
function RemountOnQuery({ children }) {
  const { search } = useLocation();
  return <React.Fragment key={search}>{children}</React.Fragment>;
}

// Numeric ids only; anything else falls through to the home page, as unknown paths do.
// Keyed by id so moving between two listings (or sellers) starts from a clean page.
function WithNumericId({ render }) {
  const { id } = useParams();
  if (!/^\d+$/.test(id)) return <HomePage />;
  return <React.Fragment key={id}>{render(Number(id))}</React.Fragment>;
}

function StartAuctionRoute() {
  const [params] = useSearchParams();
  return <StartAuctionPage listingId={Number(params.get("listing"))} category={params.get("category") === "equipment" ? "equipment" : "live_animal"} />;
}

function ListingEditorRoute() {
  const [params] = useSearchParams();
  return <ListingEditorPage editId={params.get("edit")} editCategory={params.get("category")} />;
}

// Client-side navigation keeps the scroll position, so a new page starts at the top. Only the path
// counts: changing the marketplace search or category shouldn't jump the results.
function ScrollToTopOnPathChange() {
  const { pathname } = useLocation();
  React.useLayoutEffect(() => {
    window.scrollTo(0, 0);
  }, [pathname]);
  return null;
}

export default function App() {
  const location = useLocation();
  const navigate = useNavigate();
  const onMarketplace = location.pathname === "/marketplace";
  const search = useMemo(() => readMarketplaceSearch(location.search), [location.search]);

  // On the marketplace a header search just updates the results (and the URL, without a new history
  // entry); anywhere else it navigates to the marketplace with the search applied.
  const handleHeaderSearch = (term, tags) => {
    // Searching from the marketplace keeps what's being browsed (animals or equipment).
    const category = onMarketplace ? readMarketplaceCategory(location.search) : "live_animal";
    navigate(buildMarketplaceUrl(term, tags, category), { replace: onMarketplace });
  };

  return (
    <>
      <ScrollToTopOnPathChange />
      <Header
        // Remount when the committed search changes so the search box reflects it (e.g. after "Clear all filters").
        key={`${search.term}|${search.tags.map((tag) => tag.value).join(",")}`}
        searchTerm={search.term}
        onSearch={handleHeaderSearch}
        selectedSearchTags={search.tags}
      />
      <Routes>
        <Route path="/posts/:id" element={<WithNumericId render={(id) => <ListingDetailPage listingId={id} />} />} />
        <Route path="/equipment/:id" element={<WithNumericId render={(id) => <ListingDetailPage listingId={id} category="equipment" />} />} />
        <Route path="/sellers/:id" element={<WithNumericId render={(id) => <SellerProfilePage sellerId={id} />} />} />
        <Route path="/auctions" element={<AuctionsPage />} />
        <Route path="/auctions/new" element={<RequireSignIn><RemountOnQuery><StartAuctionRoute /></RemountOnQuery></RequireSignIn>} />
        <Route path="/auctions/:id" element={<WithNumericId render={(id) => <AuctionRedirectPage auctionId={id} />} />} />
        <Route path="/postinput" element={<RequireSignIn><RemountOnQuery><ListingEditorRoute /></RemountOnQuery></RequireSignIn>} />
        <Route path="/signin" element={<RemountOnQuery><SignInPage /></RemountOnQuery>} />
        <Route path="/my-listings" element={<MyListingsPage />} />
        <Route path="/orders" element={<MyOrdersPage />} />
        <Route path="/saved-searches" element={<SavedSearchesPage />} />
        <Route path="/saved" element={<SavedListingsPage />} />
        <Route path="/settings" element={<RequireSignIn><AccountSettingsPage /></RequireSignIn>} />
        <Route path="/upgrade" element={<RequireSignIn><UpgradePage /></RequireSignIn>} />
        <Route path="/marketplace" element={<MarketplacePage searchTerm={search.term} searchTags={search.tags} onClearSearch={() => handleHeaderSearch("", [])} />} />
        <Route path="*" element={<HomePage />} />
      </Routes>
    </>
  );
}
