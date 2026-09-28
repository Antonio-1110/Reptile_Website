# Deploying Reptilian

The website runs in three places:

| Part | Where | Address |
| --- | --- | --- |
| React frontend | Vercel | `https://reptilian.app` (and `www.` redirecting to it) |
| Django API, admin and database | Heroku, with Heroku Postgres | `https://api.reptilian.app` |
| Uploaded listing photos | Amazon S3 | `https://<bucket>.s3.<region>.amazonaws.com/media/…` |

The repo is already set up for this (root `Procfile`, `requirements.txt`, `.python-version` and
`bin/post_compile` for Heroku; `Frontend/vercel.json` for Vercel). Everything secret goes into the
hosts' settings as environment variables, never into git. The steps below are the parts only the
account owner can do. Do them in order: the backend's first build needs its variables already set.

---

## 1. Amazon S3 bucket for photos

1. In the AWS console, open **S3 → Create bucket**.
   - Name: something unique such as `reptilian-photos`.
   - Region: `ap-northeast-1` (Tokyo), close to users in Taiwan.
   - Object Ownership: leave **ACLs disabled**.
   - Block Public Access: untick **Block all public access**, then tick back the two ACL options
     (keep only the two *bucket policy* options unticked). Acknowledge the warning.
2. Open the bucket → **Permissions → Bucket policy** and paste this (change the bucket name), so
   anyone can view photos but only the app can write them:

   ```json
   {
     "Version": "2012-10-17",
     "Statement": [{
       "Sid": "PublicReadListingPhotos",
       "Effect": "Allow",
       "Principal": "*",
       "Action": "s3:GetObject",
       "Resource": "arn:aws:s3:::reptilian-photos/media/*"
     }]
   }
   ```
3. Open **IAM → Users → Create user**, e.g. `reptilian-app`, with no console access. Attach an
   inline policy like this (change the bucket name):

   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Action": ["s3:PutObject", "s3:GetObject", "s3:DeleteObject"],
         "Resource": "arn:aws:s3:::reptilian-photos/media/*"
       },
       {
         "Effect": "Allow",
         "Action": "s3:ListBucket",
         "Resource": "arn:aws:s3:::reptilian-photos"
       }
     ]
   }
   ```
   (`ListBucket` lets the app see that a file name is free instead of getting "access denied".)
4. On that user, **Security credentials → Create access key** ("Application running outside AWS").
   Copy the key ID and secret for step 2. The secret is shown only once.

## 2. Heroku app for the API

With the Student Pack, claim the Heroku platform credits first (they cover an Eco dyno and the
smallest Postgres plan). Then, in the Heroku dashboard or with the `heroku` CLI:

1. **Create the app**, e.g. `reptilian-api`.
2. **Resources**: add **Heroku Postgres** (plan *Essential-0*). This sets `DATABASE_URL` for you.
   Also add **Heroku Scheduler** (used in step 5).
3. **Settings → Config Vars**: add these before the first deploy.

   | Name | Value |
   | --- | --- |
   | `DJANGO_SECRET_KEY` | a long random string: run `python -c "import secrets; print(secrets.token_urlsafe(50))"` |
   | `DJANGO_ALLOWED_HOSTS` | `api.reptilian.app,reptilian-api.herokuapp.com` (bare host names, no `https://`; use your app's real herokuapp name) |
   | `DJANGO_CORS_ALLOWED_ORIGINS` | `https://reptilian.app,https://www.reptilian.app` |
   | `DJANGO_CSRF_TRUSTED_ORIGINS` | `https://api.reptilian.app` |
   | `DJANGO_FRONTEND_URL` | `https://reptilian.app` |
   | `DJANGO_ADMINS` | your email (gets order problem reports) |
   | `DJANGO_ADMIN_URL` | a hard-to-guess path for the admin, e.g. `staff-` plus a few random letters and digits and a `/` (keep it to yourself; bots scan `/admin/`) |
   | `DJANGO_DEFAULT_FROM_EMAIL` | `Reptilian <no-reply@reptilian.app>` |
   | `DJANGO_S3_BUCKET` | `reptilian-photos` |
   | `DJANGO_S3_REGION` | `ap-northeast-1` |
   | `AWS_ACCESS_KEY_ID` | from step 1.4 |
   | `AWS_SECRET_ACCESS_KEY` | from step 1.4 |
   | `DISABLE_COLLECTSTATIC` | `1` (the repo's build hook runs it instead) |

   Don't set `DJANGO_DEBUG`: it must stay off in production.
4. **Deploy → Deployment method → GitHub**: connect `Antonio-1110/Reptile_Website`, pick the
   `master` branch, tick **Wait for CI to pass**, and **Enable Automatic Deploys**. Then press
   **Deploy Branch** once. Each deploy compiles the translations, collects the admin's static files,
   and runs the database migrations before the new version goes live.
5. **Scheduler** (open it from Resources) → add these jobs, so auctions settle and order deadlines apply:
   - Every 10 minutes: `cd backend && python manage.py close_auctions && python manage.py process_orders`
   - Every hour: `cd backend && python manage.py send_search_alerts`
   - Every day: `cd backend && python manage.py flushexpiredtokens` (clears old sign-in records)
6. **Create your staff account**:
   `heroku run -a reptilian-api "cd backend && python manage.py createsuperuser"`
7. **Custom domain**: Settings → Domains → **Add domain** `api.reptilian.app`. Heroku shows a DNS
   target like `something.herokudns.com`; copy it for step 4. Under **SSL Certificates**, choose
   **Automatic Certificate Management**.

Check: `https://reptilian-api.herokuapp.com/api/v1/posts/species/` returns JSON, and
your `DJANGO_ADMIN_URL` address shows a styled login page. After 5 wrong passwords in a row the admin
refuses sign-in for 15 minutes (`LOGIN_LOCKOUT_FAILURES`, `LOGIN_LOCKOUT_MINUTES`).

## 3. Vercel project for the frontend

1. With the Student Pack's GitHub login, **Add New → Project** → import `Antonio-1110/Reptile_Website`.
2. **Root Directory**: `Frontend`. Vercel detects Vite; leave the build settings as they are.
3. **Environment Variables**: `VITE_API_URL` = `https://api.reptilian.app/api` (Production).
   Vite bakes this into the build, so redeploy after changing it.
4. Deploy. Every push to `master` redeploys. Pull requests also get preview links on `vercel.app`
   addresses, but the API only accepts requests from the origins in `DJANGO_CORS_ALLOWED_ORIGINS`,
   so previews won't load data unless you add their address there.
5. **Settings → Domains**: add `reptilian.app`, and add `www.reptilian.app` set to redirect to it.
   Vercel shows the DNS records it wants; copy them for step 4.

## 4. DNS records at your registrar

In the domain's DNS settings (where you registered `reptilian.app`), add exactly what Vercel and
Heroku showed you. Typically:

| Type | Host | Value |
| --- | --- | --- |
| `A` | `@` | Vercel's IP (commonly `76.76.21.21`; use the one Vercel shows) |
| `CNAME` | `www` | Vercel's target (commonly `cname.vercel-dns.com`) |
| `CNAME` | `api` | the `…herokudns.com` target from step 2.7 |

Remove any parking or forwarding records the registrar added for `@` or `www`. `.app` domains only
work over HTTPS; both Vercel and Heroku issue the certificates themselves once DNS points at them,
which can take from a few minutes to an hour.

## 5. Email (before real users sign up)

Until this is done the site "sends" emails only to the Heroku logs, so contact requests, auction and
order emails, and saved-search alerts never arrive. New accounts also can't confirm their email address
(so they can't post, contact sellers or bid) and nobody can reset a forgotten password. Resend is the
simplest option (its free plan is enough to start):

1. Create a Resend account, add the domain `reptilian.app`, and add the DNS records it lists (step 4's
   registrar page). Wait for it to show **Verified**.
2. Create an API key, then add these Heroku config vars:

   | Name | Value |
   | --- | --- |
   | `DJANGO_EMAIL_BACKEND` | `django.core.mail.backends.smtp.EmailBackend` |
   | `DJANGO_EMAIL_HOST` | `smtp.resend.com` |
   | `DJANGO_EMAIL_PORT` | `587` |
   | `DJANGO_EMAIL_HOST_USER` | `resend` |
   | `DJANGO_EMAIL_HOST_PASSWORD` | the API key |

Amazon SES works the same way with its own SMTP host and credentials.

## 6. Google sign-in (optional, free)

The "Continue with Google" button appears once both apps know your Google OAuth client ID. Only the
client ID is used: it isn't secret (every visitor's browser sees it), and the client secret Google also
shows you isn't needed anywhere.

1. At <https://console.cloud.google.com>, create a project (e.g. `Reptilian`).
2. **Google Auth Platform → Branding**: app name `Reptilian`, your support email, homepage
   `https://reptilian.app`, privacy policy `https://reptilian.app/privacy`, terms of service
   `https://reptilian.app/terms`, and authorized domain `reptilian.app`. Leave the logo empty: uploading
   one makes Google review the app. Under **Audience** choose **External**.
3. **Clients → Create client**: type **Web application**. Under **Authorized JavaScript origins** add
   `https://reptilian.app`, `https://www.reptilian.app` and, for local testing, `http://localhost:5173`
   and `http://localhost`. No redirect URIs are needed. Copy the **Client ID** (it ends in
   `.apps.googleusercontent.com`).
4. **Audience → Publish app**, so any Google account can sign in, not just test users. The site asks
   only for name and email, so Google doesn't need to review it.
5. Heroku config var `DJANGO_GOOGLE_CLIENT_ID` = the client ID.
6. Vercel environment variable `VITE_GOOGLE_CLIENT_ID` = the same client ID, then redeploy.

Vercel preview links aren't in the list of origins, so the Google button won't work on them.

## 7. Final check

- `https://reptilian.app` loads, a listing page opens directly (e.g. after a refresh), and both
  languages work.
- Register, sign in, create a listing with a photo: the photo URL starts with your bucket's address.
- With step 6 done, "Continue with Google" on the sign-in page signs you in (a new Google user gets an
  account with a username made from their email address).
- `https://api.reptilian.app/<your DJANGO_ADMIN_URL>` lets the staff account in, and `/admin/` is a 404.
- `http://api.reptilian.app/…` redirects to `https://`.
