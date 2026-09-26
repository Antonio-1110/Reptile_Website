# Guide for AI Coding Agents

This is the single source of truth for any AI coding agent working in this repository (Claude Code,
Codex, Copilot, Cursor, Gemini, Aider, …). Tool-specific files (`/AGENTS.md`, `/CLAUDE.md`,
`.github/copilot-instructions.md`) only point here — edit this file, not them.

Humans are welcome too; it doubles as a fast onboarding page.

---

## 1. What this project is

A bilingual (English / Traditional Chinese) marketplace for reptile keepers in Taiwan: sellers list live
animals and equipment, buyers browse with rich filters, request a seller's contact details, report
listings, and bid in auctions.

| Part | Stack | Location |
| --- | --- | --- |
| Frontend | React 19, Vite 7, Tailwind CSS 4, i18next | `Frontend/` |
| Backend | Django 5.2, Django REST Framework 3.14, SimpleJWT, django-filter | `backend/` |
| Database | SQLite (local dev) | `backend/db.sqlite3` (not committed) |
| Reference docs | API contract, troubleshooting, vision doc | `docs/` (**git-ignored, local only**) |

Django apps in `backend/`:

- `account/` — `Account` user model (hobbyist vs commercial, paid tier, limits), profile and plans views
- `authentication/` — JWT auth at `/api/v1/auth/` (the only auth; also serves `profile/` and `plans/`)
- `post/` — listings (`LiveAnimalPost`, `EquipmentPost` on an abstract `BasePost`), `Species`, contact requests, reports, photo uploads
- `auction/` — auctions, bids, deposits; business rules live in `auction/services.py`
- `common/` — dev-only auth bypass middleware
- `backend/` — settings and root URLs

Per-app detail: [README.md](../README.md), [backend/README.md](../backend/README.md),
[Frontend/README.md](../Frontend/README.md).

---

## 2. Commands

Run from the repo root unless stated. The Python virtualenv is **`.venv/` at the repo root**.

```bash
# One-time setup
python3 -m venv .venv && .venv/bin/pip install -r backend/requirements.txt
cp backend/.env.example backend/.env            # sets DJANGO_DEBUG=1 for local dev
(cd backend && ../.venv/bin/python manage.py migrate)
(cd Frontend && npm install)

# Run both servers (backend :8000, frontend :5173, logs in .dev/logs/)
./start-dev.sh
./stop-dev.sh

# Backend
cd backend
../.venv/bin/python manage.py test                     # full suite (~1 min)
../.venv/bin/python manage.py test post.tests.ListingPhotoUploadTests   # one class
../.venv/bin/python manage.py makemigrations <app> -n <descriptive_name>
../.venv/bin/python manage.py migrate
../.venv/bin/python manage.py seed_demo --reset        # demo accounts + ~70 listings
../.venv/bin/python manage.py close_auctions           # settle auctions past their end time
../.venv/bin/python manage.py process_orders           # apply order deadlines (payment, handover, confirm)
../.venv/bin/python manage.py send_search_alerts       # email users new listings matching their saved searches
../.venv/bin/python manage.py makemessages -l zh_Hant  # after adding translatable strings
../.venv/bin/python manage.py compilemessages
../.venv/bin/python manage.py check --deploy           # production settings audit

# Frontend
cd Frontend
npm run lint
npm run build          # also catches import/JSX errors lint misses
npm run dev
```

Demo accounts (after `seed_demo`) all use password `DemoPass123!` — see the table in
[backend/README.md](../backend/README.md#demo-data) for which account exercises which scenario
(e.g. `mei_lin` is a hobbyist at the post cap, `apex_exotics` is a paid commercial seller).

---

## 3. Rules that must not be broken

These are invariants. If a task seems to require breaking one, stop and ask the user.

**Backend is the authority.**
- Validation, limits, ownership and permissions are enforced server-side. Frontend checks are only for
  fast feedback and must mirror (never replace) the backend.
- Account limits live on the `Account` model (`max_post_count`, `max_images_per_post`,
  `can_start_auction`, …). Read them from there; never hard-code 5/20/200 or 3/6/12 elsewhere.
- Post and image limits are enforced by `PostLimitSerializerMixin` (`post/serializer.py`) and the
  `photos` action (`ListingPhotoUploadSerializer`).
- Auction rules belong in `auction/services.py`, and post-sale order rules in `auction/orders.py`, not in
  views or serializers. Marketplace policy numbers (deadlines, fee, seller bond, review threshold, rate
  limits) are settings read from environment variables; never hard-code them.
- Users can never grant themselves a plan or reputation. `account_type`, `is_paid_account`,
  `verified_seller`, `seller_rating` and `total_reviews` are read-only on the profile and registration
  endpoints. Commercial is a paid upgrade that only a payment-confirmed upgrade flow may set.

**Privacy.**
- Public listing responses must not contain `contact_info`, the seller's `email`, `phone_number`,
  `personal_id`, `line_id`, `contact_email`, `instagram` or `facebook`. Account contact fields are only
  on `ProfileAccountSerializer` (the user's own profile). `OwnerOnlyContactInfoMixin` and
  `PublicSellerSerializer` implement this — reuse them for any new listing-like serializer.
- A seller's contact details are never handed to someone just for asking: that's how scrapers harvest
  them. `POST …/<id>/contact/` sends the *buyer's* details to the seller (the seller then reaches out).
  The two sides of a sale see each other's details only through their order
  (`OrderSerializer.counterpart`, gated by `orders.CONTACT_STATUSES`). `Account.contact_details()` is
  the one source for what gets shared.
- All money goes through the platform (deposits, buy-now payments) via the gateway in
  `auction/payments.py`; never add a flow where a buyer pays a seller directly.
- Only a listing's owner may modify it (`IsPostOwnerOrReadOnly`). New write actions must keep that.

**Secrets and local data never enter git.**
- `backend/.env`, `backend/db.sqlite3`, `backend/media/`, `superuser.txt`, `.venv/` are ignored.
  Don't add them, don't paste their contents into code, docs, commits or PR descriptions.
- Configuration comes from environment variables (`DJANGO_*`, see `backend/.env.example`). Never
  hard-code a secret key, host name or credential in `settings.py`.
- `DEBUG` defaults to off. Don't flip the default.

**Both languages, always.**
- Every user-facing frontend string goes through `t("…")` with the key added to **both**
  `Frontend/src/i18n/locales/en.js` and `zh.js` (Traditional Chinese, Taiwan usage).
- Terminology: a listing is **刊登** (never 商品; count it with 則), the marketplace is **市集**, and
  English calls it a "listing" (not a "post"). English headings and buttons use sentence case.
- Every user-facing backend message (validation errors, API `detail` strings, emails) is wrapped in
  `gettext` (`_()`), using `%(name)s` placeholders, then added to
  `backend/locale/zh_Hant/LC_MESSAGES/django.po` and compiled.

---

## 4. How the pieces fit

### API map

| Base path | What | Auth |
| --- | --- | --- |
| `/api/v1/auth/` | `register/`, `login/` (JWT pair), `refresh/`, `me/`, `profile/` (quota info used by the listing editor), `plans/` | JWT |
| `/api/posts/live-animals/`, `/api/posts/equipment/` | CRUD, `mine/`, `<id>/contact/`, `<id>/report/`, `<id>/photos/` | read: public; write: owner |
| `/api/posts/species/` | species lookup | public |
| `/api/auctions/` | auctions, deposits, bids | read: public; write: authenticated |
| `/media/…` | uploaded listing photos (served by Django only when `DEBUG`) | public |

Full request/response examples: `docs/API_ENDPOINTS.md` (local only). When you change the contract,
update that file **and** the API overview in the root README.

### Frontend data flow

- Routing is hand-rolled in `App.jsx` (`renderPage` matches `window.location.pathname`). No router
  library yet — add routes there.
- **All network calls go through `src/api/`.** `http.js` → `apiFetch` (adds `Accept-Language`,
  translates network errors); `authApi.js` → `authFetch` (adds JWT, refreshes once on 401, sets JSON
  `Content-Type` unless the body is `FormData`); `listingsApi.js` → listing calls and the mapping
  between UI names and API names (`lifeStage` ↔ `life_stage`, `weight` ↔ `weight_grams`, …).
- Marketplace filtering, search and pagination happen on the server (`post/filters.py`);
  the client requests one page at a time. Don't reintroduce "download everything and filter".
- Async error state uses `utils/errorState.js` (`toErrorState` / `errorText`) so messages follow a
  language switch.
- Photos: the editor saves the listing first, then `saveListingPhotos()` posts multipart to
  `<id>/photos/` with the final `order` (kept photo URLs and `new:<n>` for uploads, cover first), so
  sellers can reorder or remove photos without re-uploading; `image` is the cover and `gallery` lists
  every photo, cover first.

### Local dev auth bypass

With `DJANGO_DEBUG=1`, any request **without** credentials is treated as the superuser `dev-user`
(`common/middleware.py`). Consequences for agents:
- `curl` writes succeed without a token locally — that does **not** mean the endpoint is protected
  correctly. Verify permissions with the test suite (tests run with `DEBUG=False`) or with a real
  token for a non-owner account.
- To see the truly anonymous view, test in the suite or run with `DJANGO_DEBUG=0 DJANGO_SECRET_KEY=x`.

---

## 5. Code conventions

Match the surrounding code; when in doubt, copy the nearest similar thing.

**Backend**
- Shared behaviour across the two listing types is written once as a mixin (`ContactSellerMixin`,
  `ReportListingMixin`, `OwnListingsMixin`, `ListingPhotosMixin`) and added to both viewsets.
- Listing-type-specific relations use a pair of nullable FKs (`live_animal_post` / `equipment_post`)
  plus a `post` property — follow this pattern rather than introducing generic relations.
- `post/serializer.py` is singular; other apps use `serializers.py`.
- Use `select_related` / `prefetch_related` on list querysets; check for N+1 queries when adding
  nested serializer fields.
- SQLite can't do JSONField `contains`; see `json_list_has_any` in `post/filters.py`.
- Every model change ships with a named migration in the same change. Never edit an applied migration.
- Tests: `APITestCase`, one class per feature, descriptive `test_…` names that read as behaviour.
  `post/tests.py` is indented with **tabs** — keep each file's existing indentation. Use
  `override_settings(MEDIA_ROOT=tempdir)` for anything that writes files.

**Frontend**
- Plain JavaScript + JSX (no TypeScript). Function components and hooks only.
- One `.css` file per component, imported by that component; global tokens live in `src/index.css`.
- Shared UI goes in `components/`; components used by a single page live next to that page
  (see `pages/ListingEditor/components/`).
- Revoke `URL.createObjectURL` previews when they're replaced or unmounted (see `MediaUploader`).
- Lookup tables (locations, species, limits) belong in `src/constants/` — one source of truth each.

**Comments** explain *why* (a constraint, a trade-off, a non-obvious consequence), not *what*.

---

## 6. Working effectively as an agent

### Before you change anything
1. Read the files you'll touch **in full**, plus one example of the pattern you're extending
   (e.g. an existing mixin before adding a new one).
2. Run the relevant tests first to get a baseline, so you can tell your failures from pre-existing ones.
3. Check `git status`. Other agents or the user may be editing in parallel — the working tree can change
   under you. Prefer small exact-match edits over rewriting whole files, and re-read a file if it
   changed since you last looked.

### While changing
- Keep diffs focused on the task. Note unrelated problems in your summary (or `TODO.md`) instead of
  fixing them in passing.
- Changing an API field? Update, in the same change: serializer → tests → `src/api/*` mapping →
  components → docs.
- Adding a user-facing string? Add both translations (§3).
- Prefer existing dependencies. If a new one is warranted, add it to `backend/requirements.txt`
  (pinned) or `Frontend/package.json` and say why.

### Verify before declaring done
CI (`.github/workflows/ci.yml`) runs on every PR: backend `check`, `makemigrations --check`, the test
suite (with `DEBUG` off), and frontend `lint` + `build`. Run the same locally before pushing; CI green
is the floor, not the bar.

Tests passing is necessary, not sufficient, for web work. Pick what fits the change:

| Change | Minimum verification |
| --- | --- |
| Backend logic / permissions | `manage.py test`, including a new test for the new behaviour and its failure case |
| API contract | tests + `curl` the real endpoint and inspect the JSON shape |
| Frontend code | `npm run lint` and `npm run build` |
| UI / user flow | run both servers and exercise the flow in a browser (or with a browser-automation tool): happy path, an error path, both languages, and a narrow (~375 px) viewport |
| Settings / deploy | `manage.py check --deploy` with production-like env vars |

Useful tricks:
- The DRF browsable API (`http://127.0.0.1:8000/api/posts/live-animals/`) is the quickest way to see
  real responses and try filters.
- Start a throwaway backend on another port (`runserver 127.0.0.1:8010`) for end-to-end checks
  without disturbing the user's running server; clean up any records you create.
- In the browser, the Network tab (or your automation tool's request log) is the truth about what
  the frontend actually sent — check it before blaming the backend.
- The user's shell is zsh: quote globs in commands (`grep --include='*.jsx'`), or zsh will error with
  "no matches found".

### Report honestly
Pull requests follow `.github/pull_request_template.md`.
Say what you verified and how, what you didn't verify, and anything left for the user (migrations to
run, env vars to set, servers to restart). Never commit or push unless asked.

---

## 7. Web development checklist

Apply these whenever you build or review a feature — they're the common gaps in this kind of app.

- **Security:** authorization checked on every write and on object-level reads of private data; no
  secrets or personal data in public responses, logs or URLs; validate uploads server-side (type via
  Pillow, size, count); never trust a client-supplied owner/account id — take it from `request.user`.
- **Data integrity:** enforce invariants with database constraints where possible (see the
  `CheckConstraint`/`UniqueConstraint`s in `auction/models.py`), and use `transaction.atomic` plus
  `select_for_update` for races such as concurrent bids.
- **Performance:** paginate lists; avoid N+1 queries; debounce search input; don't block rendering on
  non-critical requests; size images sensibly.
- **UX states:** every async view has loading, empty, error and success states; disable buttons while
  submitting; errors say what to do next.
- **Accessibility:** real `<button>`/`<label>` elements, `alt` text on images, `role="alert"` for
  errors, visible focus, keyboard-reachable dialogs (use `hooks/useDialogFocus`: focus in, Tab
  trapped, Escape closes, focus returns), inputs named even when they only show a placeholder, colour
  contrast in the tokens (light text goes on `--color-accent`/`--color-accent-strong`, never on
  `--color-accent-bright`).
- **i18n:** no string concatenation for sentences (use interpolation), dates and prices formatted
  per locale, layouts that tolerate longer or shorter translations.
- **Responsiveness:** check narrow phones and wide desktops; no horizontal scrolling.
- **Resilience:** handle 401 (token expired), 403, 404 and network failure explicitly in the UI.

---

## 8. Known gotchas

- If the site shows no listings, check the backend first: `curl http://127.0.0.1:8000/api/posts/live-animals/`
  and `.dev/logs/backend.log`. A stale `.dev/pids` makes `start-dev.sh` refuse to start; run
  `./stop-dev.sh` first. `start-dev.sh` uses `.venv/` at the repo root (then `backend/.venv`, then the
  system `python3`, which usually lacks Django).
- Auth is JWT only (`/api/v1/auth/`, `authFetch` on the frontend). The old `/api/auth/` token endpoints
  were retired; a dev database may still have an unused `authtoken_token` table.
- Seeded listing photos are hot-linked Wikimedia URLs; uploaded ones are absolute URLs under
  `/media/`. Code that deletes photo files must only touch the latter (see
  `ListingPhotosMixin._delete_uploaded_photos`).
- `docs/` is git-ignored, so doc changes there don't show up in diffs or PRs.
- After pulling someone else's work, run `migrate` — unapplied migrations (e.g. `auction`) cause
  `no such table` errors in the shell and dev server.
- Auction payments (deposits, buy-now) are paid instantly when `DEBUG` is on (`InstantPaymentGateway`)
  and require staff confirmation in the admin otherwise.
- Buy-now emails are sent with `transaction.on_commit`; in tests wrap the request in
  `self.captureOnCommitCallbacks(execute=True)` or `mail.outbox` stays empty.
- `makemessages` / `compilemessages` need GNU gettext (`apt install gettext`, `brew install gettext`).
  New msgids for an existing string come out `#, fuzzy` with the old translation pre-filled: translate
  them and drop the flag, or the new text silently falls back to English.
- Rate limits are off in tests (dummy cache; see `CACHES` in settings); `common/tests.py` shows how to
  test them. Locally, logging in more than 10 times a minute (e.g. a browser-automation script) gets
  `429` responses.

---

## 9. Keeping this file useful

Update this guide in the same change when you add an app, a command, an invariant, or discover a
gotcha that cost you time. Keep it scannable — link to READMEs for detail rather than duplicating
them. Project backlog lives in [TODO.md](TODO.md).
