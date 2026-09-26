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
│   ├── http.js                # apiFetch(): every request; sends Accept-Language, translates network errors
│   ├── authApi.js             # JWT login/register/refresh, tokens, authFetch() (signed requests)
│   ├── auctionsApi.js         # auctions, deposits, bids, buy now, orders + backend <-> UI field mapping
│   └── listingsApi.js         # listings, photos, contact/report, profile + backend <-> UI field mapping
├── constants/
│   ├── listingLimits.js       # client-side mirror of backend field limits
│   ├── locations.js           # location keys <-> backend codes (single source of truth)
│   └── species.js             # backend species names -> translated labels
├── hooks/
│   ├── useDebouncedValue.js
│   └── useNow.js              # ticking clock shared by a page's countdowns
├── i18n/
│   ├── index.js               # i18next setup
│   └── locales/               # en/, zh/ — one file per section (t("favorites.save") → favorites.js), loaded by index.js
├── utils/
│   ├── auctionFormat.js       # auction phase, countdowns, money and date formatting
│   ├── cropImage.js           # canvas helper for cropping listing photos
│   ├── errorState.js          # toErrorState() / errorText(): async error messages that follow a language switch
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
    ├── SellerProfilePage      # /sellers/:id — a seller's public profile and listings
    ├── SavedSearchesPage      # /saved-searches — searches the user is emailed about (saved from the marketplace)
    ├── SavedListingsPage      # /saved — animals the user saved with ♡
    ├── AccountSettingsPage    # /settings
    ├── SignInPage             # /signin
    ├── Auctions/              # /auctions (?tab=ended); cards link to the listing's own page
    │   ├── AuctionsPage.jsx
    │   ├── AuctionRedirectPage.jsx  # /auctions/:id → the listing's page
    │   ├── StartAuctionPage.jsx     # /auctions/new?listing=&category= — start an auction (and post the seller bond)
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
`http://localhost:8000/api` (the API root; requests go to its `/v1/`).

## Scripts

- `npm run dev` — start the Vite dev server
- `npm run build` — production build
- `npm run preview` — preview the production build
- `npm run lint` — run ESLint
- `npm test` — run the tests once (Vitest + React Testing Library, jsdom); `npm run test:watch` re-runs on save.
  Tests sit next to the code they cover (`*.test.js` / `*.test.jsx`); `src/test/setup.js` loads the
  English translations and DOM matchers
- `npm run e2e` — end-to-end tests with Playwright (`e2e/`): starts a throwaway backend on :8001 with its
  own database and the demo data (`e2e/start-backend.sh`) and Vite on :5174, then drives Chromium
  through real flows (list an animal with a photo → a buyer finds it and contacts the seller; sign-in).
  First time only: `npx playwright install chromium`

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
- Photos are uploaded after the listing itself is saved: `uploadListingPhotos()` posts the files as
  multipart to `<id>/photos/`, which replaces the listing's photos; the chosen cover (cropped in the
  browser with `ImageCropModal`) comes first.

## How the pieces fit

### Who does what

| Layer | Responsibility | Doesn't |
| --- | --- | --- |
| `App.jsx` | Declares the React Router routes, derives the header search from the URL, and sends signed-out visitors to sign in for account pages (`RequireSignIn`). | Fetch page data. |
| `pages/*` | One per route. **Owns its data:** calls `src/api/`, keeps loading / error / empty / success state, and passes plain values and callbacks down. Page-only pieces sit in the page's folder (`pages/ListingDetail/components/`); a self-contained one may call the API itself (`ContactSellerPanel`, `BidPanel`) and tell the page through a callback (`onChanged`). | Build URLs or parse API responses themselves. |
| `components/*` | Shared building blocks used by several pages (cards, grid, filters, header, toast, crop dialog). **Presentational:** they get data and callbacks as props (the header is the exception: it reads the sign-in state and runs the search). | Fetch data or know which page they're on. |
| `api/*` | The only code that talks to the backend: builds requests, attaches auth and language, and **maps between API field names and the UI's** (`life_stage` ↔ `lifeStage`, location codes ↔ keys). Throws `Error`s whose `message` is ready to show. | Hold UI state. |
| `hooks/`, `utils/`, `constants/` | Pure helpers: formatting, the shared clock (`useNow`), debouncing, lookup tables. | Import React components. |

### Calling the API

- **Every request goes through `apiFetch`** (`api/http.js`), which sends `Accept-Language` so the
  backend answers in the UI language, and turns a failed connection into a translated "can't reach
  the server" error.
- **Signed-in requests use `authFetch`** (`api/authApi.js`): it adds `Authorization: Bearer <access>`,
  refreshes the access token once on a 401 and retries, sets a JSON `Content-Type` unless the body is
  `FormData`, and turns an error response into an `Error` with `message` (the API's `detail`, or its
  field messages) plus `status` and `fields` (`{field: "message"}` for forms).
- **Public reads** that don't need a user use the module's `request()` helper; auction reads use
  `authFetch` even when public, so a signed-in viewer gets their own `my_deposit` / `is_seller`.
- **Map at the edge.** `normalizeListing()` / `normalizeAuction()` / `normalizeOrder()` turn API objects
  into what components use, and the build/create functions go the other way. Components never see
  snake_case API fields.
- **Lists are paginated on the server.** Ask for one page at a time (`getListingsPage`,
  `getAuctionsPage`) with `{results, count, hasMore}` back; never download everything and filter in the
  browser.

### Async state in a page

- Keep `loading`, `error`, the data, and (for lists) `nextPage` together, and render all four states:
  loading text, `role="alert"` error with a retry button, an empty message, and the content.
- Store errors with `toErrorState(error, 'fallback.key')` and show them with `errorText(t, state)`.
  The API's message is already translated; the fallback key is translated at render time, so it
  follows a language switch.
- When a newer request can overtake an older one (typing in a filter), drop stale answers:
  `MarketplacePage` bumps a `queryIdRef` per query and ignores responses for an old id. Debounce input
  with `useDebouncedValue`.
- Pages that show countdowns call `useNow()` once and pass `now` down, so every countdown ticks
  together; `useListingAuction` also reloads the auction every 15 s and when the countdown hits zero.
- Short confirmations go in a `Toast` owned by the page (`showToast(message, tone)` passed down).

### Adding things

- **A route:** add the page under `pages/`, then a `<Route>` in `App.jsx` (wrap its element in
  `<RequireSignIn>` if it needs an account; the backend enforces access either way). Link to it with
  `<Link to>` rather than `<a href>` so navigation stays in the app.
- **An endpoint:** add a function to the matching `api/*.js` module that calls `request`/`authFetch`
  and maps the response with a `normalize*()`; update the backend README and `docs/API_ENDPOINTS.md`
  when the contract changes.
- **A user-facing string:** add the key to both `i18n/locales/en/<section>.js` and `zh/<section>.js`;
  a new feature gets a new section file in each (see Conventions).
- **A lookup table** (locations, species, limits): `constants/`, one source of truth each.

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
  dialogs and error fallbacks — with the same key added to both `i18n/locales/en/` and
  `i18n/locales/zh/` (`npm test` checks the two match). Backend messages arrive already translated (`api/http.js` sends
  `Accept-Language`), so show `error.message` from the API as-is. Chinese copy uses informal 你.
