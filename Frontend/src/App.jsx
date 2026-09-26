import React, { useState } from "react";
import Header from "./components/layout/Header";
import HomePage from "./pages/HomePage";
import MarketplacePage from "./pages/MarketplacePage";
import ListingEditorPage from "./pages/ListingEditor/ListingEditorPage";
import AccountSettingsPage from "./pages/AccountSettingsPage";
import ListingDetailPage from "./pages/ListingDetail/ListingDetailPage";
import MyListingsPage from "./pages/MyListingsPage";
import MyOrdersPage from "./pages/MyOrdersPage";
import AuctionsPage from "./pages/Auctions/AuctionsPage";
import StartAuctionPage from "./pages/Auctions/StartAuctionPage";
import AuctionRedirectPage from "./pages/Auctions/AuctionRedirectPage";
import SignInPage from "./pages/SignInPage";
import UpgradePage from "./pages/UpgradePage";
import { isLoggedIn } from "./api/authApi";
import { buildMarketplaceUrl, readMarketplaceCategory, readMarketplaceSearch } from "./utils/marketplaceSearch";

// Sends a signed-out visitor to sign in, then back to the page (query included) they asked for.
// The backend enforces auth regardless; this just avoids showing a form they can't submit.
function RedirectToSignIn() {
  React.useEffect(() => {
    const next = window.location.pathname + window.location.search;
    window.location.replace(`/signin?next=${encodeURIComponent(next)}`);
  }, []);
  return null;
}

function renderPage(pathname, search, clearSearch) {
  const detailMatch = pathname.match(/^\/posts\/(\d+)$/);
  if (detailMatch) return <ListingDetailPage key={`animal-${detailMatch[1]}`} listingId={Number(detailMatch[1])} />;
  const equipmentMatch = pathname.match(/^\/equipment\/(\d+)$/);
  if (equipmentMatch) return <ListingDetailPage key={`equipment-${equipmentMatch[1]}`} listingId={Number(equipmentMatch[1])} category="equipment" />;
  const auctionMatch = pathname.match(/^\/auctions\/(\d+)$/);
  if (auctionMatch) return <AuctionRedirectPage key={auctionMatch[1]} auctionId={Number(auctionMatch[1])} />;
  if (pathname === "/auctions") return <AuctionsPage />;
  if (pathname === "/auctions/new") {
    if (!isLoggedIn()) return <RedirectToSignIn />;
    const params = new URLSearchParams(window.location.search);
    return <StartAuctionPage listingId={Number(params.get("listing"))} category={params.get("category") === "equipment" ? "equipment" : "live_animal"} />;
  }
  if (pathname === "/postinput") {
    if (!isLoggedIn()) return <RedirectToSignIn />;
    const params = new URLSearchParams(window.location.search);
    return <ListingEditorPage editId={params.get("edit")} editCategory={params.get("category")} />;
  }
  if (pathname === "/signin") return <SignInPage />;
  if (pathname === "/my-listings") return <MyListingsPage />;
  if (pathname === "/orders") return <MyOrdersPage />;
  if (pathname === "/settings") return isLoggedIn() ? <AccountSettingsPage /> : <RedirectToSignIn />;
  if (pathname === "/upgrade") return isLoggedIn() ? <UpgradePage /> : <RedirectToSignIn />;
  if (pathname === "/marketplace") return <MarketplacePage searchTerm={search.term} searchTags={search.tags} onClearSearch={clearSearch} />;
  return <HomePage />;
}

export default function App() {
  const [pathname, setPathname] = useState(window.location.pathname);
  const [search, setSearch] = useState(readMarketplaceSearch);

  React.useEffect(() => {
    const handlePopState = () => {
      setPathname(window.location.pathname);
      setSearch(readMarketplaceSearch());
    };
    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, []);

  // On the marketplace a header search just updates the results (and the URL); anywhere else it
  // navigates to the marketplace with the search applied.
  const handleHeaderSearch = (term, tags) => {
    // Searching from the marketplace keeps what's being browsed (animals or equipment).
    const category = pathname === "/marketplace" ? readMarketplaceCategory() : "live_animal";
    const url = buildMarketplaceUrl(term, tags, category);
    if (pathname !== "/marketplace") {
      window.location.href = url;
      return;
    }
    window.history.replaceState(null, "", url);
    setSearch({ term: term.trim(), tags });
  };

  return (
    <>
      <Header
        // Remount when the committed search changes so the search box reflects it (e.g. after "Clear all filters").
        key={`${search.term}|${search.tags.map((tag) => tag.value).join(",")}`}
        searchTerm={search.term}
        onSearch={handleHeaderSearch}
        selectedSearchTags={search.tags}
        setSelectedSearchTags={(tags) => setSearch((current) => ({ ...current, tags }))}
      />
      {renderPage(pathname, search, () => handleHeaderSearch("", []))}
    </>
  );
}
