# Frontend — Reptile Marketplace UI

React + Vite single-page app for browsing listings, posting animals/equipment, and managing seller
accounts.

## Tech stack

- React 19, Vite 7
- i18next / react-i18next (English + Chinese)
- Tailwind CSS 4

## Layout

```text
Frontend/src/
├── index.jsx                  # entry point (mounts <App />, loads i18n)
├── App.jsx                    # path-based routing
├── index.css                  # global tokens (colors) + Tailwind base reset
├── api/
│   ├── auctionsApi.js         # auctions, deposits and bids + backend <-> UI field mapping
│   ├── authApi.js             # JWT login/register/refresh, authFetch()
│   └── listingsApi.js         # listing CRUD + backend <-> UI field mapping
├── constants/
│   ├── listingLimits.js       # client-side mirror of backend field limits
│   └── locations.js           # location keys <-> backend codes (single source of truth)
├── hooks/
│   ├── useDebouncedValue.js
│   └── useNow.js              # ticking clock shared by a page's countdowns
├── i18n/
│   ├── index.js               # i18next setup
│   └── locales/               # en.js, zh.js — one translation object per language
├── utils/
│   ├── auctionFormat.js       # auction phase, countdowns, money and date formatting
│   ├── cropImage.js           # canvas helper for cropping listing photos
│   └── marketplaceSearch.js   # search term + tags + category <-> /marketplace URL
├── assets/
├── components/                # shared across pages
│   ├── layout/                # Header
│   ├── listings/              # ListingCard, ListingGrid, EndOfResultsCard
│   ├── auctions/              # AuctionCountdown (auction cards + listing page)
│   ├── filters/               # FilterSidebar and its sections (FilterSection, RangeFilter, …)
│   └── ui/                    # generic widgets: Toast, ImageCropModal, LanguageSwitcher, CategorySwitch
└── pages/                     # one file per route
    ├── HomePage               # /
    ├── MarketplacePage        # /marketplace
    ├── ListingDetail/         # /posts/:id (animal) and /equipment/:id — one page per listing, for sale or being auctioned
    │   ├── ListingDetailPage.jsx
    │   ├── useListingAuction.js   # the listing's latest auction + bids, refreshed while it runs
    │   ├── useListingTranslation.js  # t() that prefers `key_equipment` variants on equipment pages
    │   └── components/        # BidPanel, BuyNowPanel, OrderPanel (after a sale), ContactSellerPanel, AuctionHistoryCard
    ├── MyListingsPage         # /my-listings
    ├── MyOrdersPage           # /orders — the user's orders as buyer and seller
    ├── SavedListingsPage      # /saved — animals the user saved with ♡
    ├── AccountSettingsPage    # /settings
    ├── SignInPage             # /signin
    ├── Auctions/              # /auctions (?tab=ended); cards link to the listing's own page
    │   ├── AuctionsPage.jsx
    │   ├── AuctionRedirectPage.jsx  # /auctions/:id → the listing's page
    │   └── components/        # AuctionCard
    └── ListingEditor/         # /postinput (create) and /postinput?edit=<id>&category= (edit)
        ├── ListingEditorPage.jsx
        └── components/        # form sections used only by this page
```

## Setup

```bash
cd Frontend
npm install
npm run dev
```

Runs at `http://localhost:5173`. Set `VITE_API_URL` if the backend isn't at
`http://localhost:8000/api`.

## Scripts

- `npm run dev` — start the Vite dev server
- `npm run build` — production build
- `npm run preview` — preview the production build
- `npm run lint` — run ESLint

## Talking to the backend

- All API calls go through `src/api/` — `authApi.js` for auth, `listingsApi.js` for listings, `auctionsApi.js` for
  auctions.
- The marketplace never downloads every listing: filters and search are sent to the backend
  (`getListingsPage()`), and `MarketplacePage` fetches the next 20 results when a sentinel below the grid
  comes within 800px of the viewport. Filter edits are debounced; responses for an outdated query are
  ignored. When the results run out, `EndOfResultsCard` closes the feed (or stands in for an empty one).
- The Live Animals / Equipment switch at the top of the filter sidebar (the same `CategorySwitch` as the
  listing editor) decides what the whole page shows: which endpoint `getListingsPage()` calls, which
  filters the sidebar offers and are sent, and how `ListingCard` draws a card. It's kept in the URL
  (`?category=equipment`).
- Authenticated requests send `Authorization: Bearer <access token>` (JWT from `/api/v1/auth/`);
  `authFetch()` refreshes an expired access token once and retries.
- `api/listingsApi.js` converts UI field names to backend serializer names before
  submitting (e.g. `lifeStage` → `life_stage`, `weight` → `weight_grams`, `size` → `size_cm`).
- `constants/listingLimits.js` mirrors backend validation constraints (string lengths, numeric ranges) so
  the form can give immediate feedback, but the backend is the enforcement source of truth for account
  post/image quotas — see [backend/README.md](../backend/README.md).
- The backend currently accepts image URLs only; `MediaUploader.jsx` keeps local file previews but
  submits an empty gallery until a real upload endpoint exists.

## Conventions for contributors

- **File names match the default export**, in PascalCase for components/pages (`ListingCard.jsx`
  exports `ListingCard`), camelCase for plain modules (`listingsApi.js`). Pages end in `Page`.
- **Every component with styles has a same-named `.css` next to it** (`Toast.jsx` + `Toast.css`) and
  imports it itself. No inline `style={{}}` or Tailwind utility classes in JSX.
- **CSS class names are prefixed with the component name** in kebab-case (`listing-detail-price`,
  `crop-modal-save`) so styles from different files can't collide. State modifiers are `is-*`
  (`is-selected`) or BEM-style `--variant` classes (`toast--error`).
- **Where things go:** shared by several pages → `components/<area>/`; used by exactly one page →
  that page's folder (`pages/ListingEditor/components/`); constants → `constants/`; backend calls →
  `api/`.
- Keep UI-side validation (`constants/listingLimits.js`, form checks) in sync with backend
  model/serializer rules rather than as the only source of truth.
- Every user-facing string goes through i18n — text, placeholders, `alt`/`aria-label`, confirm
  dialogs and error fallbacks — with the same key added to both `i18n/locales/en.js` and
  `i18n/locales/zh.js`. Backend messages arrive already translated (`api/http.js` sends
  `Accept-Language`), so show `error.message` from the API as-is. Chinese copy uses informal 你.
