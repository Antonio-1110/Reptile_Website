# Project Ideas and TODO

Backlog for humans and AI agents. When you finish an item, tick it in the same change. When you notice
a problem outside your task, add it here rather than fixing it in passing. How to work in this repo:
[AGENTS.md](AGENTS.md).

## High priority

- [ ] Finalize the frontend/backend data contract for listing creation and profile updates
- [ ] Validate hobbyist vs commercial account workflows end-to-end
- [x] Add server-side enforcement for post limits and image limits
- [ ] Review and clean up API response shapes for the frontend
- [ ] Confirm authentication flow works in the browser for login and signup
- [ ] Better UI for choosing the image section for the post cover
- [ ] Consolidate auth on JWT (`/api/v1/auth/`) and retire the legacy token endpoints in `account/`
      (move `profile/` over first; the listing editor depends on it)
- [x] Frontend for auctions: browse (`/auctions`), detail, pay deposit, bid, results, seller cancel
- [ ] UI for starting an auction (paid commercial sellers, e.g. from My Listings), with the optional
      buy-now price, plus a seller-bond payment screen; today both are API-only (`POST /api/auctions/`,
      `/api/auctions/seller-bond/`) and `seed_demo` creates auctions
- [ ] Decide what happens to held auction deposits when a seller deletes the listing or an account is
      deleted: today it cascades and the deposit records disappear. Probably block deletion while an
      auction is active or deposits are held
- [ ] Schedule `manage.py close_auctions` and `manage.py process_orders` (cron / worker, every few
      minutes) wherever the backend is hosted
- [x] Buy now: optional seller price, paid in full up front, first payment wins and closes the
      auction, deposits refunded, everyone emailed; contact details only shared after a paid sale
- [x] Orders: winner pays the rest within a deadline or loses the deposit; seller may then offer the
      runner-up; seller hands over within N days; buyer confirms or reports a problem within M days
      (sale completes if they do neither); seller no-show refunds the buyer. Emails at every step
- [x] Track accounts behaving oddly (incidents + admin "Accounts to review"); nothing auto-blocked
- [ ] Decide the real numbers: payment / handover / confirm windows, fee, seller bond amount, review
      threshold, anti-sniping window. All are env-var settings with placeholder defaults (see `backend/.env.example`)
- [ ] Payouts: completed orders show the seller's payout, but paying sellers is manual (admin
      "Mark the seller as paid out"); automate with the payment processor
- [ ] "My orders" page listing a user's orders as buyer and seller; today orders only show on the
      animal's page (and in emails)
- [ ] After a sale falls through (winner defaulted, offer declined), the public page still shows the
      auction's winning bid; show the listing as available again or let the seller relist it
- [ ] Equipment has no public detail page, so equipment auctions have nowhere to be shown
- [x] Add Traditional Chinese translations for the new photo-upload errors ("Cover index is out of
      range.", "\"%(name)s\" is larger than 5 MB.") via `makemessages` / `compilemessages`

## Security and deployment

- [x] Hide seller contact info and email from public listing responses
- [x] Move `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS` and CORS settings to environment variables
- [ ] Decide on hosting, then set `SECURE_SSL_REDIRECT` / `SECURE_HSTS_SECONDS` (the remaining
      `check --deploy` warnings)
- [ ] Serve `MEDIA_ROOT` in production (web server or object storage such as S3/R2); Django only
      serves uploads when `DEBUG` is on
- [ ] Switch production to PostgreSQL; SQLite is dev-only
- [ ] Real email backend (SMTP or a provider) for contact-request emails
- [x] Rate-limit login, register, contact, report and payment endpoints (DRF throttling)
- [ ] With several backend workers, point `CACHES` at a shared cache (e.g. Redis) so rate limits are exact
- [ ] Encrypt `personal_id` if seller verification starts collecting it
- [x] Fix `start-dev.sh` to find the virtualenv at the repo root `.venv/` (it only checked `backend/.venv`)

## Feature ideas

- [x] Upgrade page at `/upgrade` with a plan comparison (limits from `GET /api/auth/plans/`) and a
      placeholder checkout
- [ ] Real upgrade checkout: a payment provider (ECPay / NewebPay) and a server-side endpoint that sets
      `account_type` / `is_paid_account` only after payment is confirmed. The profile and registration
      endpoints deliberately can't change the account type, so this is the only way in (auctions
      already require a paid account)
- [x] Add image upload support with per-account limits
- [x] Add richer filtering for location, price and species (live animals)
- [x] Add richer filtering for equipment (price range, search tags, equipment category): new
      `category` field (set in the editor with `condition`) and `EquipmentPostFilter`
- [ ] Equipment browse page: the equipment filters exist on the API, but the marketplace only lists
      live animals
- [x] Add listing detail pages
- [ ] Add seller profile pages (`/sellers/<id>`) with bio, rating, verified badge and active listings
- [ ] Add saved favorites or watchlist functionality (optional price-drop alerts)
- [ ] Listing status: available / reserved / sold, so sold items aren't deleted
- [ ] Reviews that update `seller_rating` / `total_reviews`, allowed only after a `ContactRequest`
- [x] Let users report listings for moderation
- [ ] Admin review workflow for reports (pending/resolved, hide listing, auto-hide after N reports)
- [ ] Structured genetics: a `Gene` model per species (recessive / co-dominant / dominant, het %)
      replacing the free-text `genetics` field
- [ ] Pairing calculator: predicted offspring odds for two morphs, linking to matching listings
- [ ] Species care sheets (temperature, humidity, diet, enclosure) linked from listings
- [ ] Permit / CITES field and warnings for protected species
- [ ] In-app buyer–seller messaging instead of exchanging phone and LINE details
- [ ] Saved searches with email alerts (search state is already in the URL)
- [ ] Seller verification workflow for `verified_seller`
- [ ] Let sellers reorder or remove individual photos without re-uploading all of them

## UX improvements

- [ ] Responsive header: below ~1180px the signed-in links don't fit next to the search bar (they
      overlap it on tablets and phones). Needs a menu/drawer on narrow screens
- [x] `ListingCard` nests the seller `<a>` inside the card `<a>` (React warns "<a> cannot be a
      descendant of <a>"); make the card a non-link container with a stretched title link
- [x] Anti-sniping for auctions: extend the end time when a bid lands in the last few minutes
      (`AUCTION_EXTEND_WINDOW_MINUTES` / `AUCTION_EXTEND_BY_MINUTES`, default 5 / 5)

- [ ] Improve the home page copy and layout polish
- [ ] Refine English and Chinese wording consistency across the app
- [ ] Improve empty states and loading states for listings and profile pages
- [ ] Add clearer success/error messages for posting and login flows
- [ ] Show existing photos in the listing editor when editing (it currently only allows a replacement set)
- [ ] Accessibility pass: keyboard navigation in the crop modal and filters, focus management, contrast

## Technical backlog

- [ ] Standardize API naming and response fields across backend endpoints
- [x] Add tests for account validation, posting rules, and serializer behavior
- [x] Review and clean up duplicate or legacy documentation files
- [x] Consider a clearer separation between public listing endpoints and seller-only actions
- [ ] Document frontend component responsibilities and API integration patterns
- [ ] Frontend tests: Vitest + React Testing Library for `src/api/` mapping and key components
- [ ] End-to-end tests (e.g. Playwright) for sign in → create listing with photos → view → contact seller
- [x] CI (GitHub Actions): backend tests, `npm run lint`, `npm run build` on every PR
      (`.github/workflows/ci.yml`; also fails on a model change without its migration)
- [ ] Replace hand-rolled routing in `App.jsx` with React Router once more routes land
- [ ] Decide whether `docs/` should be tracked in git (it's currently ignored, so doc updates never reach PRs)
- [ ] Remove the empty `.github/appmod/` folder if it's no longer used

## Nice-to-have

- [ ] Add admin dashboard for managing users and listings
- [ ] Add analytics for listing views and conversions
- [ ] Add notifications for new messages or inquiries
- [ ] Add a ranking or recommendation system for listings

## Notes

The core listing, contact and auction flows now exist on the backend. The most valuable next steps are
the auction UI, consolidating auth, and the deployment items above, before building much more on top.
