# Reptile Marketplace

A reptile marketplace app with a React + Vite frontend and a Django REST API backend.

## Project overview

This project is organized into two main app areas:

- **Frontend** — React UI for browsing listings, posting animals/equipment, and managing seller
  accounts. See [Frontend/README.md](Frontend/README.md).
- **Backend** — Django + DRF API for authentication, listings, filtering, and seller logic. See
  [backend/README.md](backend/README.md).

## Tech stack

- Frontend: React 19, Vite, Tailwind CSS, i18next
- Backend: Django 5, Django REST Framework
- Database: SQLite for local development
- Auth: token-based authentication via Django REST Framework's authtoken
- CORS: enabled for local frontend development ports

## Repository structure

```text
reptile_website/
├── .github/
│   ├── AGENTS.md               # guide for AI coding agents (source of truth)
│   └── copilot-instructions.md # Copilot summary, points to AGENTS.md
├── AGENTS.md / CLAUDE.md       # pointers to .github/AGENTS.md for agents that look at the root
├── backend/
│   ├── account/            # auth + seller profile
│   ├── post/                # listings, species, image/post limits
│   ├── backend/              # project settings, urls
│   ├── manage.py
│   ├── requirements.txt
│   ├── db.sqlite3            # local dev database
│   └── README.md
├── Frontend/
│   ├── src/
│   ├── public/
│   ├── package.json
│   ├── vite.config.js
│   ├── index.html
│   └── README.md
├── docs/
│   ├── README.md               # index of docs and what each one is for
│   ├── API_ENDPOINTS.md         # current API contract (source of truth)
│   ├── DEV_TROUBLESHOOTING.md   # seeding data, db reset, curl examples
│   └── SYSTEM_DESIGN.md         # original architecture vision doc
├── start-dev.sh
├── stop-dev.sh
└── README.md
```

## Local setup

### Start and stop both services

From the project root:

```bash
./start-dev.sh
./stop-dev.sh
```

This runs the backend at `http://127.0.0.1:8000` and the frontend at `http://127.0.0.1:5173`. Runtime
logs are written under `.dev/logs/`.

### Frontend only

```bash
cd Frontend
npm install
npm run dev
```

Runs at `http://localhost:5173`. Details in [Frontend/README.md](Frontend/README.md).

### Backend only

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # sets DJANGO_DEBUG=1; without it Django refuses to start with no secret key
python3 manage.py migrate
python3 manage.py runserver
```

Runs at `http://127.0.0.1:8000/`. Details in [backend/README.md](backend/README.md).

## API overview

Full request/response examples live in [docs/API_ENDPOINTS.md](docs/API_ENDPOINTS.md).

### Authentication (`/api/v1/auth/`, JWT)

- `POST /register/`, `POST /login/` (returns `access` + `refresh`), `POST /refresh/`, `GET /me/`
- `GET`/`PATCH /profile/` (auth required) — includes current post/image usage and remaining quota
- `GET /plans/` — public plan comparison

### Posts (`/api/posts/`)

- `GET`/`POST /live-animals/`, `GET`/`PATCH`/`DELETE /live-animals/<id>/`
- `GET`/`POST /equipment/`, `GET`/`PATCH`/`DELETE /equipment/<id>/` — equipment has a `category`
  (`enclosure`, `heating`, `lighting`, `climate`, `substrateDecor`, `transport`, `other`) and a
  `condition` (0–2); the list filters by both, plus price, location, shipping and posting date
- `GET /species/` — each with its `aliases`. A live-animal listing takes `species` (an id) or
  `requested_species` (a typed name): a name that isn't a species or alias is held for staff review,
  and the listing stays unpublished (`species_review`) until staff map or add the species

### Auctions (`/api/auctions/`)

- `GET /`, `GET /<id>/` — public; each auction includes a `listing` summary (title, cover photo,
  species, genes) for cards, and the anti-sniping rule (`extend_window_minutes`, `extend_by_minutes`):
  a bid near the end extends `ends_at`
- `POST /` — paid commercial accounts only
- `POST /<id>/deposit/`, `GET`/`POST /<id>/bids/`, `POST /<id>/cancel/`, `POST /<id>/buy-now/`,
  `GET`/`POST /seller-bond/` (auth required)
- `/orders/`: after a sale, the buyer's and seller's view of it (pay, hand over, confirm, report a
  problem, runner-up offers)

Notes:

- Anyone may read published listings; only the listing's owning account may update or delete it.
- Token auth is required for authenticated requests; CORS allows local frontend ports (`5173`, `3000`).
- The backend models and serializers are the source of truth for field names and validation rules.

## Account model rules

The project supports a distinction between hobbyist and commercial users:

- Hobbyist accounts: no rating requirement, lower post/image limits
- Commercial accounts: rating is relevant, higher limits (higher still when paid)

This split is enforced on the `Account` model (see [backend/README.md](backend/README.md#domain-model))
and must stay consistent between model, serializer, and frontend copy.

## Post and image limit guidance

Post and image constraints are enforced in backend serializer logic (`PostLimitSerializerMixin`), not
only on the frontend, so the rules remain consistent across all clients. The frontend mirrors these
limits for immediate user feedback but is never the enforcement authority.

## Contributor notes

- Keep frontend and backend responsibilities separated; treat the backend as the source of truth for
  API contracts.
- Update [docs/API_ENDPOINTS.md](docs/API_ENDPOINTS.md) when adding new fields, routes, permissions, or
  account rules.
- Open work and planned features are [GitHub Issues](https://github.com/Antonio-1110/Reptile_Website/issues); a PR that finishes one says
  "Closes #n" in its description.
