# Backend — Reptilian API

Django + Django REST Framework API powering authentication, listings, and seller logic.

## Tech stack

- Django 5.2
- Django REST Framework 3.14
- django-cors-headers, django-filter
- SQLite for local development
- JWT authentication (`djangorestframework-simplejwt`)

## App layout

```text
backend/
├── account/            # auth + seller profile
│   ├── models.py       # Account model (extends AbstractUser)
│   ├── serializers.py  # register/login/profile serializers
│   ├── views.py        # UserRegister, UserLogin, UserLogout, UserProfile
│   ├── urls.py
│   └── migrations/
├── auction/            # auctions, bids and bidder deposits (/api/v1/auctions/)
│   ├── models.py       # Auction, Bid, Deposit
│   ├── services.py     # all auction rules: deposits, bidding, cancelling, settling
│   ├── payments.py     # PaymentGateway interface + manual/instant gateways
│   ├── ecpay.py        # ECPay card payments: checkout form, result callbacks, refunds
│   ├── orders.py       # after a sale: Order (pay the rest, hand over, confirm), seller bond, incidents
│   ├── notifications.py # every auction/order email
│   └── management/commands/close_auctions.py, process_orders.py
├── authentication/     # JWT register/login/refresh/me (/api/v1/auth/)
├── common/
│   └── middleware.py   # DevAuthBypassMiddleware + DRF auth classes (DEBUG only)
├── post/               # marketplace listings
│   ├── models.py       # BasePost, LiveAnimalPost, EquipmentPost, Species
│   ├── serializer.py   # includes shared PostLimitSerializerMixin
│   ├── views.py        # LiveAnimalViewSet, EquipmentViewSet, SpeciesViewSet
│   ├── urls.py
│   └── migrations/
├── backend/            # project settings
│   ├── settings.py
│   ├── urls.py         # mounts everything under /api/v1/
│   └── wsgi.py / asgi.py
├── manage.py
├── requirements.txt
└── db.sqlite3          # local dev database
```

## Setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 manage.py migrate
python3 manage.py runserver
```

Runs at `http://127.0.0.1:8000/`.

## Demo data

```bash
python3 manage.py seed_demo            # 13 demo accounts, ~60 animal + 12 equipment listings, contacts, reports
python3 manage.py seed_demo --reset    # wipe previous demo data and recreate it
python3 manage.py seed_demo --delete   # remove demo data only
python3 manage.py feature auctions on  # auctions start switched off; turn them on to see the demo auctions
```

All demo accounts share the password `DemoPass123!` and use `@demo.morphmarket.test` emails, which is
how `--reset`/`--delete` find them — real accounts are never touched. The command prints every
username with its role and post quota. Useful ones:

| Username | What it's good for testing |
| --- | --- |
| `apex_exotics`, `highridge_geckos` | Paid, verified commercial sellers with many listings |
| `morph_kingdom`, `dragon_den_tw`, `shell_and_scale` | Unpaid commercial sellers (20-post cap) |
| `mei_lin` | Hobbyist exactly at the 5-post cap ("limit reached" UI) |
| `kevin_chen`, `tina_turtles`, `jay_wu` | Hobbyist sellers with room to post |
| `buyer_amy`, `buyer_jason`, `buyer_hsu` | Buyers who have already contacted/reported listings |
| `new_user_sam` | Brand-new account with no activity |

Listing photos are freely licensed images hotlinked from Wikimedia Commons.

It also creates 9 auctions on `apex_exotics`' and `highridge_geckos`' animals: some ending within the
hour, running, not started yet, with no bids, and already ended. The buyers and the unpaid commercial
sellers have deposits and bids on them. `new_user_sam` has no deposits, so use it to try the deposit →
bid flow. Log in as `apex_exotics` to see the seller's view.

## Running tests

```bash
python3 manage.py test
```

## Domain model

### Account (`account/models.py`)

- `account_type`: `hobbyist` or `commercial`
- `is_paid_account`: unlocks higher commercial limits
- `seller_rating`, `total_reviews`, `verified_seller`, `bio`
- Limits are computed on the model, not hardcoded in views/serializers:
  - `max_post_count` / `max_images_per_post` properties
  - `can_create_post()` / `can_upload_images()` helpers

| Account         | Posts | Images per post |
| --------------- | ----: | --------------: |
| Hobbyist        |     5 |               3 |
| Commercial      |    20 |               6 |
| Paid commercial |   200 |              12 |

- `can_start_auction`: only commercial accounts (either plan) may start auctions (the paywall); anyone may bid.
  Commercial pays `AUCTION_FEE_RATE_COMMERCIAL` on auction sales and Commercial Pro `AUCTION_FEE_RATE_PRO`;
  sellers who joined before `LAUNCH_OFFER_JOINED_BEFORE` pay none for `LAUNCH_OFFER_DAYS` after joining.

### Posts (`post/models.py`)

- `BasePost` is an abstract base shared by `LiveAnimalPost` and `EquipmentPost` (title, description,
  price, location, contact_info, shipping_methods, timestamps, owning `account` FK).
- `Species` is a simple lookup table used by `LiveAnimalPost`.
- Post/image quotas are enforced server-side via `PostLimitSerializerMixin` in `post/serializer.py`,
  applied to both `LiveAnimalPostSerializer` and `EquipmentPostSerializer`, so limits can't be bypassed
  by any client.
- Only the owning seller may update or delete their own listing (`IsPostOwnerOrReadOnly` permission in
  `post/views.py`); reads and creation follow standard `IsAuthenticatedOrReadOnly` rules.
- `ContactRequest` records one-click buyer inquiries instead of open-ended messaging: the `contact`
  action (`ContactSellerMixin` in `post/views.py`) emails the seller the *buyer's* contact details
  (`Account.contact_details()`) so the seller can reach out. `GET` previews exactly what will be sent.
  The seller's own details are never returned, so accounts can't be used to harvest them. Only the
  first request per buyer/listing pair triggers an email.
- `Report` records buyers flagging a listing for manual moderation review (`ReportListingMixin` /
  `report` action in `post/views.py`). Only the first report per reporter/listing pair is stored.
  Moderation rules live in `post/moderation.py`. In the admin, Reports filtered by "Pending review" is
  the queue: **Hide the reported listings and resolve**, **Resolve**, or **Dismiss** (which shows the
  listing again); each records who reviewed it and when. Listing admin pages show pending report counts
  and can hide/unhide. A hidden listing (`is_hidden`) is 404 to everyone but its owner (who sees a
  notice) and staff. With `REPORT_AUTO_HIDE_THRESHOLD` > 0, a listing reported by that many different
  accounts hides itself and staff are emailed; 0 (the default) only queues reports.
- `OwnListingsMixin` adds a `/mine/` action (`post/views.py`) so sellers can list only their own
  listings; standard update/delete endpoints (already owner-restricted) power editing and removal.

### Auctions (`auction/`)

- A commercial seller puts one of their own listings up for auction (`Auction`, one active
  auction per listing) with a starting price, minimum increment and end time.
- Before bidding, a buyer pays a **deposit** to the platform (`Deposit`, one per bidder per auction).
  Its amount is fixed at auction creation from `AUCTION_DEPOSIT_RATE` (10% of the starting price) with
  a floor of `AUCTION_MIN_DEPOSIT`. Only a `held` deposit allows bidding.
- Each bid must be at least the starting price, then the current price + `min_increment`. Bidders are
  anonymous to each other.
- **Anti-sniping:** a bid within `AUCTION_EXTEND_WINDOW_MINUTES` of the end moves `ends_at` to
  `AUCTION_EXTEND_BY_MINUTES` after that bid (never earlier than it was), so a last-second bid can
  still be answered. A window of `0` turns it off. Both are env vars (default 5 / 5) and are echoed on
  each auction as `extend_window_minutes` / `extend_by_minutes`.
- `python manage.py close_auctions` (run it every minute from cron) settles auctions past their end
  time. It records the winning bid, opens an **order** for the winner, keeps the winner's deposit
  `held` and refunds everyone else's. It then emails the winner, the seller and the other bidders.
  Sellers may cancel an auction only while it has no bids, which refunds every deposit.
- **Buy now** (optional): the seller may set a `buy_now_price` above the starting price. Any buyer can
  pay it in full, up front (`BuyNowPurchase`); the auction closes only when a payment arrives. Several
  buyers may be paying at once. When a second one starts, the seller and every paying buyer are
  emailed that it's a race. The first payment to arrive wins (the auction row is locked, and a
  database constraint allows one paid purchase). Everyone else's pending payment is cancelled and any
  later payment refunded in full. Winning closes the auction, refunds every bidder's deposit and
  emails the buyer, the seller and the bidders. Buy-now disappears once bidding reaches its price.
- All auction rules live in `auction/services.py`, order rules in `auction/orders.py` and emails in
  `auction/notifications.py`. Views, admin actions and future payment webhooks call these.

### Orders: after a sale (`auction/orders.py`)

Every sale becomes an `Order`, and all money stays with us until the buyer has the animal:

1. **Pay.** The auction winner pays the rest of the price (their deposit counts toward it) within
   `ORDER_PAYMENT_HOURS`. A buy-now order starts already paid.
2. **Hand over.** Once paid, the seller has `ORDER_HANDOVER_DAYS` to hand the animal over or ship
   it, then marks it handed over (optionally with a courier / tracking note).
3. **Confirm.** The buyer then has `ORDER_CONFIRM_DAYS` to confirm it arrived healthy, or to report a
   problem. If they do neither, the sale completes. Completed orders show the seller's `payout` (price
   minus the auction's `fee_rate`, fixed when it started); staff pay out by hand and tick **Mark the seller as paid out**.

When it falls through:

- **The winner doesn't pay in time.** Their deposit is kept and an incident is recorded. The seller
  is emailed and can offer the animal to the next-highest bidder at that bidder's own bid. The
  runner-up gets `ORDER_RUNNER_UP_OFFER_HOURS` to accept by paying, or can decline with no penalty.
- **The seller doesn't hand over in time.** The buyer is refunded everything and an incident is
  recorded. If sellers post bonds, the seller's bond is forfeited.
- **The buyer reports a problem.** The deadlines stop and the money stays frozen. Staff (emailed via
  `DJANGO_ADMINS`) resolve it in the Order admin: **refund the buyer** (counts against the seller) or
  **complete the sale**.

`python manage.py process_orders` applies these deadlines; schedule it next to `close_auctions`.
Buyer and seller see each other's contact details from the moment the winner is decided (the winner
has paid a deposit), or once a runner-up / buy-now buyer has paid. Nobody else ever does.

**Seller bond (optional).** With `SELLER_BOND_AMOUNT` above 0, sellers must post that bond
(`GET`/`POST /api/v1/auctions/seller-bond/`) before starting an auction. It is forfeited if they take a
buyer's money and never hand over. At 0 (the default) nothing changes.

**Accounts to review.** Incidents are recorded automatically: buy-now payments started and never
paid, winners who didn't pay, sellers who didn't hand over, disputes lost. The admin's **Accounts to
review** page adds them up per account (plus reports against their listings) and flags anyone at
`INCIDENT_REVIEW_THRESHOLD` or more. Nothing is blocked automatically; to act, deactivate the account.

All of these timings and amounts are placeholders read from environment variables (see
`.env.example`), so they can change without a code change.

### Rate limits

Login and registration (`auth`), "contact seller" (`contact`), reports (`report`), and deposits /
buy-now / order payments (`payments`) are throttled per user, or per IP address when signed out
(`DEFAULT_THROTTLE_RATES` in settings, overridable with `DJANGO_THROTTLE_*`). Over the limit the API
returns `429`. Counts live in Django's cache: the default is per process, so use a shared cache with
several workers. The test suite runs with a dummy cache so limits never trip between tests.

Deposit statuses: `pending` → `held` → `released` (refunded) or `captured` (kept); a payment
that never completes becomes `failed` (the bidder may retry) or `cancelled`.

Order statuses: `offered` (runner-up) / `awaiting_payment` → `paid` → `handed_over` → `completed`,
or `disputed` → `completed` / `refunded`; `buyer_defaulted`, `declined`, `seller_defaulted` when it
falls through. Once the sale can't go ahead any more (and the seller has no runner-up offer left to
make), the auction reports `sale_fell_through: true` (`orders.sale_fell_through`) and the listing page
shows the listing as for sale again instead of the old winning bid.

Buy-now purchase statuses: `pending` → `paid` (won; we hold the money) or `refunded` (paid after
someone else, or after the auction closed); `failed` if the payment never goes through, `cancelled`
if the auction closed first.

**Payments.** All money goes to the platform first, through the gateway named by
`AUCTION_PAYMENT_GATEWAY` (`auction/payments.py`):

- `InstantPaymentGateway` is the default when `DEBUG` is on. Every payment counts as paid at once, so
  the flows can be tried locally.
- `ManualPaymentGateway` is used otherwise. Payments stay `pending` until staff use **Mark as paid**
  in the Deposit / Buy-now purchase admin (e.g. after a bank transfer). Refunds are done by hand.

- `ECPayGateway` (`auction/ecpay.py`) takes card payments through ECPay's hosted card page. Set
  `AUCTION_PAYMENT_GATEWAY=auction.ecpay.ECPayGateway` and the `ECPAY_*` variables (see `.env.example`;
  it lists ECPay's public test merchant). Paying returns a `redirect_form` that the frontend posts to
  ECPay. ECPay reports back to `/payments/ecpay/notify/` (server to server) and
  `/payments/ecpay/result/` (the payer's browser, which then goes back to the site), so
  `DJANGO_BACKEND_URL` must be the API's public address. A payer who returns to an unfinished payment
  gets a fresh checkout. Refunds and releases go through ECPay's DoAction API. Deposits can be held on
  the card and released for free once `ECPAY_MANUAL_SETTLEMENT` is on, which needs automatic settlement
  switched off in ECPay's back office.

  To try it locally, set the test merchant in `backend/.env` and pay with ECPay's test card
  (4311-9522-2222-2222, any future expiry date, CVV 222). The browser return confirms the payment
  even though ECPay can't reach `localhost` for the server-to-server call.

## API summary

See [docs/API_ENDPOINTS.md](../docs/API_ENDPOINTS.md) for full request/response examples.

Every endpoint lives under `/api/v1/` (plural kebab-case URL segments, `snake_case` JSON). Errors have
one shape (`common/exceptions.py`): `{"detail": "message"}` for the request as a whole, always a single
string, and/or `{"field": ["message", …]}`. Serializer errors that aren't about one field go in `detail`
(`NON_FIELD_ERRORS_KEY`), and an `AuctionError` raised by `auction/services.py` or `auction/orders.py`
becomes a 400 on its own, so views don't catch it. Listings and auctions embed the seller as a `seller`
object (`PublicSellerSerializer`: public standing only, no contact details or plan limits).

### Auth (`/api/v1/auth/`, JWT)

The only authentication is JWT (SimpleJWT); the old token endpoints under `/api/auth/` were retired.
Each refresh token works once: `refresh/` returns a new pair and retires the old refresh token, and
`logout/` retires the current one.

- `POST /register/` — `username`, `email`, `password`; returns `id`, `username`, `email` (no token)
- `POST /login/` — `username` (or the account's email, any case) and `password`; returns `access`
  (60 min) and `refresh` (7 days) tokens
- `POST /google/` — `credential` (the ID token from Google's sign-in button); returns tokens like
  `login/` plus `created`. Signs in to the account linked to that Google account, else the one with
  its email address (confirming it; an unconfirmed account's password is cleared, in case someone
  else registered with that address), else creates one with no password. Off (400) until
  `DJANGO_GOOGLE_CLIENT_ID` is set
- `POST /refresh/` — `refresh` → new `access` and `refresh` (the old refresh token stops working)
- `POST /logout/` — `refresh`; retires it (401 if it's invalid or already retired)
- `GET /me/` (auth required) — `id`, `username`, `email`, `email_verified`, `verified_seller`
- `POST /verify-email/` — `uid`, `token` from the sign-up email; confirms the address (no sign-in needed)
- `POST /verify-email/resend/` (auth required) — emails a new confirmation link
- `POST /password-reset/` — `email`; emails a reset link to accounts using it (same answer either way);
  also how a Google-only account sets a password
- `POST /password-reset/confirm/` — `uid`, `token`, `password`; sets it, confirms the email and signs
  the account out everywhere
- `POST /password-change/` (auth required) — `current_password`, `password`; signs the account out on
  every other device, emails the owner, and returns a fresh `access` and `refresh` for this one. Accounts
  with no password (`has_password: false` on the profile) get 400 and set one with `password-reset/`

New accounts start with `email_verified: false` and get 403 on posting, contacting sellers, reporting,
bidding and paying until they open the emailed link (`authentication/permissions.py`). Changing the email
on the profile needs a new confirmation. Staff, seeded and pre-existing accounts count as verified.

Send the access token as `Authorization: Bearer <access>`.

```bash
B=http://127.0.0.1:8000/api/v1/auth

curl -X POST $B/register/ -H 'Content-Type: application/json' \
  -d '{"username":"alice","email":"alice@example.com","password":"S3curePass!23"}'

curl -X POST $B/login/ -H 'Content-Type: application/json' \
  -d '{"username":"alice","password":"S3curePass!23"}'
# → {"refresh": "...", "access": "..."}

curl $B/me/ -H "Authorization: Bearer <access>"

curl -X POST $B/refresh/ -H 'Content-Type: application/json' -d '{"refresh":"<refresh>"}'

# Dev bypass: no token + DEBUG=True → you are "dev-user"
curl $B/me/
```

### Account (`/api/v1/account/`)

- `GET`/`PATCH /profile/` (auth required) — the user's own profile, including `post_count` and
  `remaining_post_count`. A new `username` is refused for `USERNAME_CHANGE_DAYS` (default 30) after the
  last change, and a name another account gave up in that time is taken; names differing only in case
  count as the same (`account/usernames.py`). `username_change_available_at` says when it may change next
- `GET /plans/` — public: the account plans and their limits

### Dev auth bypass (DEBUG only)

When `DEBUG = True`, anonymous requests are treated as a `dev-user` superuser (created on first use,
unusable password), so the API and admin work without logging in. A valid JWT/token/session still takes
priority, and an *invalid* JWT still returns 401. It is fully inert when `DEBUG = False` (including
under `manage.py test`). Three pieces in `common/middleware.py` make this work:

- `DevAuthBypassMiddleware` — in `MIDDLEWARE` right after `AuthenticationMiddleware`; attaches the dev
  user to `request.user` for plain Django views (e.g. admin).
- `DevAuthBypassAuthentication` — last in `DEFAULT_AUTHENTICATION_CLASSES`; DRF re-resolves
  `request.user` itself, so it needs its own fallback.
- `DevAwareSessionAuthentication` — replaces DRF's `SessionAuthentication` so the bypass user isn't
  treated as a session login (which would force CSRF on every anonymous POST).

Note: in dev, the frontend never sees a "logged out" user on DRF endpoints. Set `DEBUG = False` to test
real login flows.

### Posts (`/api/v1/posts/`)

- `GET`/`POST /live-animals/`, `GET`/`PATCH`/`DELETE /live-animals/<id>/`
- `GET`/`POST /equipment/`, `GET`/`PATCH`/`DELETE /equipment/<id>/`
- `GET /species/`
- `POST /live-animals/<id>/photos/`, `POST /equipment/<id>/photos/` (owner, multipart) — set the
  listing's photos. Either `photos` + `cover_index` (the uploads replace everything), or `order`: a JSON
  list of the final photos, cover first, where each entry is one of the listing's current photo URLs
  (kept) or `new:<n>` (the n-th file in `photos`). Current photos left out are removed, and uploaded
  files among them are deleted. The account's image limit applies to the total.
- Listings have a `status`: `available` (default), `reserved` or `sold`, set by the owner with `PATCH`.
  List endpoints leave sold listings out unless `?status=` asks for them (e.g. `?status=sold`); a sold
  listing keeps its page, can't be contacted about or auctioned, and a completed auction sale marks the
  listing sold.
- `GET`/`POST /saved-searches/`, `PATCH`/`DELETE /saved-searches/<id>/` (signed in) — the user's saved
  marketplace searches: `query` is the live-animals list query (e.g. `search=pied&sex=1.0`), checked
  against the real filters and stored sorted; `name` defaults to the search text. Up to
  `SAVED_SEARCH_LIMIT` per account. `python manage.py send_search_alerts` (schedule it, e.g. every few
  hours) emails each user the listings posted since their last alert that match, with links built from
  `DJANGO_FRONTEND_URL`.
- `POST`/`DELETE /live-animals/<id>/favorite/` (and `equipment/…`) — save or unsave a listing (signed in);
  `GET /live-animals/favorites/` lists the user's saved listings, newest first. Listing responses carry
  `is_favorite` for the viewer. Lowering a listing's price emails everyone who saved it (one email each).

Filtering, search, and ordering are provided by `django-filter` and DRF's `SearchFilter`/`OrderingFilter`.
List endpoints are paginated (20 per page: `?page=N`, response has `count`/`next`/`results`).

`GET /live-animals/` accepts the marketplace filters (`post/filters.py`); list params are comma-separated
and each `*_exclude` variant inverts its counterpart:

- `search` (title, description, genetics, species name), `species_name`, `genes=Pastel,Pied` (all required)
- `sex`, `life_stage` / `life_stage_exclude`, `location` / `location_exclude` (backend codes, e.g. `TPE`)
- `diets` / `diets_exclude`, `shipping` / `shipping_exclude` (match any)
- `price_min|max`, `size_min|max`, `weight_min|max`, `age_min|max`, `posted_days_min|max`

`GET /equipment/` shares `location` / `location_exclude`, `price_min|max`, `posted_days_min|max`,
`shipping` / `shipping_exclude` and `?search=` (title, description), and adds:

- `category` / `category_exclude` (`enclosure`, `heating`, `lighting`, `climate`, `substrateDecor`,
  `transport`, `other`)
- `condition` (`2` new, `1` used, `0` not functional; comma-separated)

### Sellers (`/api/v1/sellers/`)

- `GET /<id>/` — public profile: display name, username, account type, verified badge, rating, review
  count, bio, member since and listing counts. No contact details. Only accounts that have listed
  something have one (404 otherwise), so account ids don't reveal buyers' names. Their listings come
  from `GET /api/v1/posts/live-animals/?seller=<id>` (and `equipment/?seller=<id>`). For a signed-in viewer
  it also says `can_review` and includes `my_review`.
- `GET /<id>/reviews/` — public, newest first; reviewers appear by username only. `POST` (signed in,
  `{rating: 1-5, comment}`) writes or updates your review; only someone who contacted the seller about
  a listing, or completed an auction purchase from them, may (403 otherwise). `DELETE` removes yours.
  `seller_rating` / `total_reviews` are recomputed from the reviews on every change (`account/reviews.py`)
  and are never set directly.

### Auctions (`/api/v1/auctions/`)

- `GET /` (filters: `status`, `seller`, `live_animal_post`, `equipment_post`), `GET /<id>/`
- `POST /` — commercial accounts only (`403` otherwise)
- `GET /mine/` — the current user's auctions as a seller
- `GET /rules/` — public: currency, duration limits, deposit rate/minimum and whether a seller bond is
  required (the "start an auction" form explains and pre-checks these)
- `POST /<id>/deposit/` — start or look up the current user's deposit; safe to repeat
- `GET`/`POST /<id>/bids/` — bid history / place a bid (`{"amount": "5100.00"}`); a late bid can push
  the auction's `ends_at` back (anti-sniping, see above)
- `POST /<id>/cancel/` — seller only, only while there are no bids
- `POST /<id>/buy-now/` — pay the buy-now price in full; safe to repeat
- `GET`/`POST /seller-bond/` — the seller bond (only required when `SELLER_BOND_AMOUNT` > 0)
- `GET /orders/` (`?auction=<id>`, `?role=buyer|seller`, `?status=`), `GET /orders/<id>/` — your orders as buyer or seller, with the other
  side's contact details once allowed
- `POST /orders/<id>/pay/`, `handed-over/` (seller, optional `note`), `confirm/`, `report-problem/`
  (`text`), `runner-up/` (seller, `{"offer": true|false}`), `decline/` (runner-up)

## Translations

API messages follow the `Accept-Language` header the frontend sends (`en` or `zh-Hant`), via Django's
`LocaleMiddleware`. Django, DRF and SimpleJWT ship their own Traditional Chinese translations; ours
live in `locale/zh_Hant/LC_MESSAGES/django.po`.

When you add or change a user-facing message, wrap it in `gettext` (`from django.utils.translation
import gettext as _`), then:

```bash
python3 manage.py makemessages -l zh_Hant --ignore=".venv/*" --ignore="*/migrations/*" --ignore="*/tests.py"
# fill in the new msgstr entries in locale/zh_Hant/LC_MESSAGES/django.po
python3 manage.py compilemessages --ignore=".venv/*"
```

Only the `.po` file is committed. The compiled `django.mo` is git-ignored because git can't merge a
binary file; `start-dev.sh`, the test runner (`common/test_runner.py`) and CI build it with
`compilemessages`, which needs GNU gettext. **When you deploy**, run `compilemessages` as part of the
build (next to `collectstatic`), or the API answers in English only.

Emails to sellers are sent in every supported language, since accounts don't store a language
preference yet.

## Conventions for contributors

- Enforce account/post/image rules in model or serializer logic, never only on the frontend.
- Keep the `account` FK as the single source of truth for listing ownership.
- Add or update tests in `account/tests.py` / `post/tests.py` when changing validation or permission rules.
- Reflect new fields or routes in [docs/API_ENDPOINTS.md](../docs/API_ENDPOINTS.md).
