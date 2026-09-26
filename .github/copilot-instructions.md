# Instructions for GitHub Copilot

The full, tool-agnostic guide for AI coding agents is **[.github/AGENTS.md](AGENTS.md)**. Read it
before making changes; it has the commands, architecture, conventions and verification steps.
Edit that file, not this one. This file only repeats the rules that matter most, for contexts that
load nothing else.

## Essentials

- Reptilian (reptile marketplace): React 19 + Vite frontend in `Frontend/`, Django 5 + DRF backend in `backend/`
  (apps: `account`, `authentication` (JWT, used by the frontend), `post`, `auction`, `common`).
- Python virtualenv is `.venv/` at the repo root. Test with
  `cd backend && ../.venv/bin/python manage.py test`; lint and build with
  `cd Frontend && npm run lint && npm run build`.
- The backend is the authority for validation, limits and permissions. Account limits come from the
  `Account` model; auction rules live in `auction/services.py`.
- Never expose `contact_info` or seller email/phone/ID in public listing responses. Contact details
  are only released through the authenticated `…/<id>/contact/` action.
- Only a listing's owner may modify it or upload its photos.
- Configuration comes from `DJANGO_*` environment variables (`backend/.env.example`). Never commit
  `.env`, `db.sqlite3`, `media/` or `superuser.txt`.
- Every user-facing string needs English and Traditional Chinese: frontend keys in both
  `src/i18n/locales/en.js` and `zh.js`; backend messages wrapped in `_()` and added to
  `backend/locale/zh_Hant/LC_MESSAGES/django.po`.
- All frontend network calls go through `Frontend/src/api/` (`authFetch` for authenticated requests).
- Model changes ship with a named migration; API changes update serializer, tests, `src/api/`
  mapping and docs together.
