# Reptile Marketplace — System Design Document

**Version:** 1.0  
**Author:** ChatGPT  
**Date:** 2025-11-21

---

## 1. Project Overview

A web marketplace where users can post reptiles and related equipment (cages, lighting, food, accessories) for sale. Primary goals:

- Easy posting with rich media (images, short videos)
- Reliable user accounts and messaging between buyer and seller
- Searchable listings with filters (species, age, location, price, category)
- Safe content and legal compliance for animal sales
- Scalable, maintainable architecture using React (frontend), Python backend, MySQL database, and Amazon S3 for media


## 2. High-level Architecture

**Components**

- **Frontend:** React SPA (or React + Next.js if SEO / server-side rendering desired).
- **API / Backend:** Python (FastAPI or Flask + Flask-Restful; FastAPI recommended for async and auto docs).
- **Database:** MySQL (primary source of truth for users, posts, metadata).
- **Media storage:** Amazon S3 for images/videos + CloudFront CDN for delivery & caching.
- **Auth / Sessions:** JWT for API auth or session cookies (for SSR). Consider OAuth2 for social logins.
- **Background workers:** Celery (with Redis or RabbitMQ) for async tasks: thumbnail generation, video transcoding, notifications, moderation jobs.
- **Cache / Rate limiting:** Redis (caching common queries, session store, rate limiter).
- **Search:** Simple SQL search with indexed fields OR adopt Elasticsearch / OpenSearch for advanced search & filtering if scale requires.
- **Monitoring & Logging:** Prometheus + Grafana (metrics), ELK or Loki (logs), Sentry (errors).
- **CI/CD & Deployment:** Docker images, GitHub Actions / GitLab CI, deploy to AWS ECS/Fargate, Kubernetes (EKS) or serverless (AWS Lambda + API Gateway) depending on team skillset.

**Data flow (simplified)**

1. User uploads post data via React form.
2. Frontend obtains presigned S3 URLs from backend and uploads images/videos directly to S3.
3. Frontend sends post metadata (title, description, media keys, price, location, species tags) to backend API.
4. Backend writes post record to MySQL and pushes async jobs: create thumbnails, generate searchable index, run moderation.
5. Listing becomes available; CDN serves the media files.


## 3. Key Design Decisions & Rationale

- **Presigned S3 uploads** — Avoids sending binary data through the backend, reduces server load and bandwidth costs.
- **FastAPI + async endpoints** — Handles concurrent connections efficiently, auto-generates OpenAPI docs for frontend developers.
- **MySQL for relational data** — Good fit for normalized user and listing data; use InnoDB and proper indexing.
- **Use a search engine (OpenSearch)** when listings and filter complexity grows; initial MVP can rely on well-indexed MySQL queries.
- **Background processing** — Offload computationally expensive tasks (video processing, thumbnails, moderation) to workers.
- **CDN + caching** — Deliver media quickly and reduce S3 egress.
- **Microservices vs Monolith** — Start with a modular monolith (single backend repo with clear modules) and split into services if/when scale demands.


## 4. Data Model (Suggested Tables)

Below are essential tables and important fields. Add indexes as noted.

### `users`
- `id` (PK)
- `username` (unique, indexed)
- `email` (unique, indexed)
- `password_hash`
- `display_name`
- `phone` (nullable)
- `is_verified` (bool)
- `role` (enum: user, moderator, admin)
- `created_at`, `updated_at`

### `profiles` (optional, for extended user info)
- `user_id` (FK -> users.id)
- `bio`
- `location` (city, state, country)
- `address` (optional)
- `reputation_score` (computed)

### `listings`
- `id` (PK)
- `user_id` (FK -> users.id)
- `title`
- `description` (text)
- `price` (decimal)
- `currency` (3-letter code)
- `category` (enum: live_animal, enclosure, heating, food, accessories, other)
- `species` (nullable string or FK to species table)
- `age` (nullable)
- `condition` (enum: new, used, adult, juvenile)
- `location_lat`, `location_lng` (for geospatial search)
- `location_address` (text)
- `status` (enum: draft, active, sold, removed)
- `created_at`, `updated_at`

### `media`
- `id` (PK)
- `listing_id` (FK)
- `s3_key`
- `media_type` (image, video)
- `mime_type`
- `width`, `height`, `duration` (for video)
- `thumbnail_s3_key`
- `order_index`

### `messages`
- `id` (PK)
- `from_user_id`, `to_user_id`
- `listing_id` (nullable)
- `body`
- `created_at`
- `is_read`

### `transactions` (optional — for escrow/payments)
- `id` (PK)
- `listing_id`, `buyer_id`, `seller_id`
- `amount`, `currency`
- `status` (pending, completed, refunded)
- `payment_provider_id` (external reference)

### `species` (optional taxonomy)
- `id`, `scientific_name`, `common_name`, `conservation_status`, `legal_restrictions`

### Indexes & notes
- Index `listings` on `(status, created_at)` for feed queries.
- Index `listings` on `(price)` and `(category)` and `(species)`.
- Spatial index on `location_lat/lng` (or use a separate geolocation store) for radius queries.


## 5. API Design (Representative endpoints)

Use RESTful endpoints or GraphQL. Representative REST endpoints:

**Auth & User**
- `POST /api/v1/auth/register` — create user
- `POST /api/v1/auth/login` — returns JWT
- `GET /api/v1/users/:id` — user profile
- `POST /api/v1/users/:id/verify` — identity verification flow

**Listings**
- `GET /api/v1/listings` — query listings (filters: q, category, species, min_price, max_price, lat, lng, radius, sort)
- `GET /api/v1/listings/:id` — listing details
- `POST /api/v1/listings` — create listing (body contains metadata; media keys optional)
- `PUT /api/v1/listings/:id` — update listing
- `POST /api/v1/listings/:id/publish` — publish listing (runs checks)
- `DELETE /api/v1/listings/:id` — remove listing

**Media**
- `POST /api/v1/media/presign` — request presigned S3 URLs for upload. Backend validates content type, size limits, user ownership and returns one or many presigned URLs and S3 keys.
- `DELETE /api/v1/media/:id` — remove media reference (also delete from S3 via background job)

**Messaging & Transactions**
- `POST /api/v1/messages` — create message
- `GET /api/v1/messages?thread_id=` — fetch messages for a thread
- `POST /api/v1/transactions` — start a transaction (if using built-in payments)

**Admin & Moderation**
- `GET /api/v1/moderation/queue` — list flagges posts
- `POST /api/v1/moderation/:id/action` — approve/reject/remove


## 6. Media Handling & Processing

- **Upload strategy:** frontend requests presigned PUT or POST S3 URL; uploads directly to S3.
- **Validation:** backend enforces upload size, file type, and per-user daily upload limits.
- **Post-upload jobs:**
  - Generate thumbnails for images and videos (worker uses ffmpeg for video).
  - Create multiple image sizes and webp derivatives for responsive delivery.
  - Extract and store EXIF metadata where relevant (but strip sensitive geotags by default to protect privacy).
  - Video transcoding for consistent playback (H.264 / MP4) and create short preview GIFs if needed.
- **Delivery:** configure CloudFront CDN in front of S3; use signed URLs if private content required.


## 7. Security & Privacy

- **Auth:** store only salted password hashes (bcrypt/argon2). Use HTTPS everywhere. Use refresh tokens for long-lived sessions.
- **Access control:** validate ownership for edits/deletes; role-based access for moderation endpoints.
- **Upload security:** validate mime types, use virus scanning on uploads (ClamAV in a worker), disallow executable uploads.
- **PII handling:** do not expose users’ raw addresses publicly; allow buyer and seller to exchange shipping details through private messages.
- **Rate limiting & throttling:** protect API endpoints (Redis-backed token bucket).
- **Audit logs:** record moderation, deletion, and payment-related actions.
- **GDPR/Privacy:** provide controls for data deletion and export if you expect EU users.


## 8. Moderation & Legal Compliance

Because this site deals with live animals, add special attention to legal and ethical compliance:

- **Terms & Rules:** explicit prohibited species, shipping rules, minimum seller requirements (e.g., verified phone, ID checks).
- **Geo-restrictions:** block listings for species illegal in buyer/seller’s region. Integrate a `legal_restrictions` field in `species` table and validate upon publish.
- **Automated checks:** flag posts that mention protected species, endangered species terms, or suspicious phrases.
- **Human moderators:** moderation queue for flagged content; ability to suspend users.
- **Age checks:** ensure compliance with laws concerning sale of certain species.
- **Shipping & transport:** do not provide guidance that violates animal welfare; require sellers to follow local transport rules.

**Recommendation:** consult a lawyer in each target jurisdiction to ensure compliance with local wildlife and animal welfare laws.


## 9. Performance & Scalability

- **Short term (MVP)**: single instance backend + MySQL RDS, Redis cache, S3, CloudFront. Optimize with DB indexes and query tuning.
- **Medium term:** read replicas for MySQL, separate media service, introduce OpenSearch for full-text search, auto-scaling for backend.
- **Long term:** split services (auth, listings, media, search), use Kubernetes or serverless patterns, use multi-AZ/multi-region databases if cross-region users.

**Caching strategies**
- Use Redis to cache common listing queries and user sessions.
- Set appropriate Cache-Control headers for media served through CDN.


## 10. Observability & Maintenance

- **Metrics:** replies/sec, requests latency (p95/p99), error rates, queue length, S3 egress.
- **Logs:** structured request logs, user actions (post/create/delete), moderation logs.
- **Alerts:** high error rate, failed worker jobs, full disk on DB, suspicious spikes in new accounts.
- **Backups:** automated RDS snapshots; periodic export of MySQL data for long-term retention. Test recovery process regularly.


## 11. UX Considerations (Frontend features)

- Clean listing form with guided fields for species, age, condition and required legal checklist.
- Image/video preview and re-ordering before publish.
- Mobile-first responsive design and accessibility (WCAG basics).
- Location auto-complete (Google Places or other) but strip geotag EXIF on images by default.
- Messaging UI with push-notifications (web push / email / SMS optional).
- User profiles, seller ratings, recent activity.
- Filters and sort options (price, distance, newest).


## 12. Suggested Improvements & Optional Add-ons

- **Escrow / Payment integration** (Stripe Connect, PayPal, or a marketplace payment provider) to facilitate secure payments.
- **Identity verification** for sellers (ID scan + phone verification) to reduce fraud and meet legal obligations.
- **Advanced search** using OpenSearch: fuzzy matching, facets (species, age, condition), geospatial radius queries.
- **Automated moderation with models**: integrate ML-based image moderation (AWS Rekognition or open-source models) to flag possible animal welfare issues or prohibited species.
- **Subscription plans / Featured listings** to monetize platform (paid pinning, promoted listings).
- **Internationalization (i18n)** if you plan to serve multiple countries.
- **Progressive Web App (PWA)** for offline capability and mobile-like experience.


## 13. Sample Sequence: Create Listing

1. User clicks "Create Listing" in React app.
2. Frontend `POST /api/v1/media/presign` with file metadata.
3. Backend returns presigned S3 URLs and S3 keys.
4. Frontend uploads files directly to S3 using presigned URLs.
5. Frontend `POST /api/v1/listings` with metadata + list of media S3 keys.
6. Backend writes entry to MySQL and enqueues background tasks (thumbnails, moderation, index for search).
7. Background worker processes media and updates `media` row(s) and listing state if any moderation flags appear.
8. Listing visible to public if status is `active`.


## 14. Example SQL snippets

**Create listings table (simplified)**

```sql
CREATE TABLE listings (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  user_id BIGINT NOT NULL,
  title VARCHAR(255) NOT NULL,
  description TEXT,
  price DECIMAL(12,2),
  currency CHAR(3) DEFAULT 'USD',
  category VARCHAR(64),
  species VARCHAR(128),
  status VARCHAR(32) DEFAULT 'draft',
  location_lat DOUBLE,
  location_lng DOUBLE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_status_created (status, created_at),
  INDEX idx_species (species),
  INDEX idx_price (price)
);
```


## 15. Risks & Mitigations

- **Legal risk (illegal wildlife trade):** mitigation — strict species policy, human moderation, legal consultation, geo-blocking, identity verification.
- **Fraud / Scams:** mitigation — rating system, identity verification, escrow payments, manual review for high-value trades.
- **Scalability surprises:** mitigation — measure, load-test, scale critical pieces (DB read replicas, CDN, worker pools).
- **Content abuse:** mitigation — reporting flow, rate limits, automated moderation.


## 16. Roadmap (MVP → v1 → v2)

- **MVP (0–3 months):** user auth, listing create/view, presigned S3 uploads, basic search/filters, messaging, moderation queue (manual), responsive UI.
- **v1 (3–9 months):** payments, identity verification, OpenSearch integration, video processing, seller ratings, basic analytics.
- **v2 (9–18 months):** advanced moderation (ML), multi-region support, mobile apps or PWA, subscriptions/promotions.


---

If you want, I can:

- Generate a more detailed ER diagram or sequence diagrams.
- Produce the OpenAPI spec for the endpoints.
- Create a starter code scaffold (FastAPI backend + React frontend) with working presigned S3 upload flow.

Tell me which of those you want and I’ll produce it next.

