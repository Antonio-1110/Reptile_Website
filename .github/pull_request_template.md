<!-- Keep it short. Link issues rather than repeating them. Never paste secrets, .env values or personal data. -->

## What and why

<!-- One or two sentences: what this changes and the problem it solves. Add "Closes #n" for the issue it finishes. -->

## Changes

<!-- The notable changes, grouped by area. Delete the areas you didn't touch. -->

- **Backend:**
- **Frontend:**
- **Docs / config:**

## How it was verified

<!-- Say what you actually ran or checked, per .github/AGENTS.md § "Verify before declaring done". -->

- [ ] `manage.py test` (new tests for the new behaviour and its failure case)
- [ ] `manage.py makemigrations --check` (model changes ship with a named migration)
- [ ] `npm run lint` and `npm run build`
- [ ] Tried in the browser: happy path, an error path, both languages, narrow (~375 px) viewport
- [ ] `curl`ed changed endpoints and checked the JSON shape

## Screenshots

<!-- For UI changes: before/after, and a phone-width shot. Delete if not applicable. -->

## Checklist

- [ ] New user-facing text is translated in **both** languages (`en.js` + `zh.js`, or `_()` + `django.po`)
- [ ] Rules and limits are enforced on the backend; the frontend only mirrors them
- [ ] Public responses still hide seller contact details and personal data
- [ ] API changes are reflected in `src/api/*`, the READMEs and `docs/API_ENDPOINTS.md`
- [ ] Issue linked with "Closes #n"; follow-ups opened as new issues

## Follow-ups / needs a decision

<!-- Anything left out on purpose, known limitations, or questions for the reviewer. Delete if none. -->
