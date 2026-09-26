# Backend — Reptile Marketplace API

Django + Django REST Framework API powering authentication, listings, and seller logic.

## Tech stack

- Django 5.2
- Django REST Framework 3.14
- django-cors-headers, django-filter
- SQLite for local development
- JWT authentication (`djangorestframework-simplejwt`), plus legacy token auth (`rest_framework.authtoken`)

## App layout

```text
backend/
├── account/            # auth + seller profile
│   ├── models.py       # Account model (extends AbstractUser)
│   ├── serializers.py  # register/login/profile serializers
│   ├── views.py        # UserRegister, UserLogin, UserLogout, UserProfile
│   ├── urls.py
│   └── migrations/
├── auction/            # auctions, bids and bidder deposits (/api/auctions/)
│   ├── models.py       # Auction, Bid, Deposit
│   ├── services.py     # all auction rules: deposits, bidding, cancelling, settling
│   ├── payments.py     # DepositGateway interface + manual/instant gateways
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
│   ├── urls.py         # mounts /api/auth/ and /api/posts/
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

- `can_start_auction`: only paid commercial accounts may start auctions (the paywall); anyone may bid.

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
  `report` action in `post/views.py`); reviewed via the `Report` admin list. Only the first report per
  reporter/listing pair is stored.
- `OwnListingsMixin` adds a `/mine/` action (`post/views.py`) so sellers can list only their own
  listings; standard update/delete endpoints (already owner-restricted) power editing and removal.

### Auctions (`auction/`)

- A paid commercial seller puts one of their own listings up for auction (`Auction`, one active
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
   minus `ORDER_FEE_RATE`); staff pay out by hand and tick **Mark the seller as paid out**.

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
(`GET`/`POST /api/auctions/seller-bond/`) before starting an auction. It is forfeited if they take a
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

To take real payments, subclass `PaymentGateway` for the processor and point the setting at it. Put
whatever the frontend needs to send the payer to checkout in `PaymentResult.client_data`. Then add a
webhook view that calls `services.confirm_deposit()` / `fail_deposit()` and `confirm_buy_now()` /
`fail_buy_now()`.

## API summary

See [docs/API_ENDPOINTS.md](../docs/API_ENDPOINTS.md) for full request/response examples.

### Auth (`/api/auth/`)

- `POST /register/`, `POST /login/`, `POST /logout/` (auth required)
- `GET`/`PATCH /profile/` (auth required) — includes `post_count` and `remaining_post_count`

### JWT auth (`/api/v1/auth/`)

- `POST /register/` — `username`, `email`, `password`; returns `id`, `username`, `email` (no token)
- `POST /login/` — returns `access` (60 min) and `refresh` (7 days) tokens
- `POST /refresh/` — `refresh` → new `access`
- `GET /me/` (auth required) — `id`, `username`, `email`, `is_verified`

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

### Posts (`/api/posts/`)

- `GET`/`POST /live-animals/`, `GET`/`PATCH`/`DELETE /live-animals/<id>/`
- `GET`/`POST /equipment/`, `GET`/`PATCH`/`DELETE /equipment/<id>/`
- `GET /species/`
- `POST /live-animals/<id>/photos/`, `POST /equipment/<id>/photos/` (owner, multipart) — set the
  listing's photos. Either `photos` + `cover_index` (the uploads replace everything), or `order`: a JSON
  list of the final photos, cover first, where each entry is one of the listing's current photo URLs
  (kept) or `new:<n>` (the n-th file in `photos`). Current photos left out are removed, and uploaded
  files among them are deleted. The account's image limit applies to the total.

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

### Auctions (`/api/auctions/`)

- `GET /` (filters: `status`, `seller`, `live_animal_post`, `equipment_post`), `GET /<id>/`
- `POST /` — paid commercial accounts only (`403` otherwise)
- `GET /mine/` — the current user's auctions as a seller
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

Emails to sellers are sent in every supported language, since accounts don't store a language
preference yet.

## Conventions for contributors

- Enforce account/post/image rules in model or serializer logic, never only on the frontend.
- Keep the `account` FK as the single source of truth for listing ownership.
- Add or update tests in `account/tests.py` / `post/tests.py` when changing validation or permission rules.
- Reflect new fields or routes in [docs/API_ENDPOINTS.md](../docs/API_ENDPOINTS.md).
