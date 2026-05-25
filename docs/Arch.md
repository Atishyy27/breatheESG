# ARCHITECTURE FREEZE — BREATHE ESG PROTOTYPE

## 1. Core Core Tech Stack
* **Backend Framework:** Django + Django REST Framework (DRF)
* **Frontend Architecture:** Vanilla React via CDN (Single Index.html, zero compilation overhead)
* **Primary Database:** PostgreSQL
* **Production Deployment Host:** Railway
* **Asset Asset Delivery:** WhiteNoise (Serving Frontend directly out of Django)

## 2. Core Relational Data Model
* `RawUpload` - Tracks file asset metadata and cryptographic hashes for duplicate prevention.
* `RawRecord` - Immutable block storage tracking raw source payload string lines for deep audit lineage.
* `NormalizedActivity` - Converged master schema storing unified carbon footprint profiles.
* `ValidationIssue` - Captures schema structural syntax/semantic anomalies without blocking ingest steps.
* `EmissionFactor` - Internal database register housing greenhouse gas conversion variables.

## 3. Operational State Machine Matrix
* `PENDING` - Freshly normalized dataset item waiting for analyst processing.
* `SUSPICIOUS` - Flagged by the rules layer due to structural baseline spikes or missing contexts.
* `APPROVED` - Verified and frozen by an analyst. Database-level seal blocks further edits.
* `REJECTED` - Dismissed from the active queue while remaining in database logs for full audit tracing.

## 4. Hard Scope Exclusions (Do Not Build)
* No user authentication models (Hardcoded analyst emails in operational request headers).
* No multi-stage approval workflow hierarchies or notification relays.
* No asynchronous task workers (Celery/Redis) — process inline for small file footprints.
* No containerization layers (Docker/Docker-Compose) or active CI/CD compilation blocks.
* No live outward third-party ESG API connectors.