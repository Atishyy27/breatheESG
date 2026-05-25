# Architecture Freeze Matrix

## 1. Technical Stack Core
- **Backend Framework**: Django 5.x + Django REST Framework (DRF)
- **Frontend Architecture**: Vanilla React (v18) injected via unpkg CDN inside a single HTML file served directly by Django's static asset layer (WhiteNoise). **Zero node_modules build step complexity.**
- **Database Engine**: PostgreSQL (Production) / SQLite (Local verification)
- **Deployment Endpoint Target**: Railway (Single application service container hosting monolithic API + template build)

## 2. Frozen Entity Model Definitions
- `RawUpload`: Tracks immutable incoming file metadata and cryptographic MD5 content checksum blocks to guarantee system idempotency.
- `RawRecord`: Stores precise, unparsed row string representations linked directly to individual raw lines for strict lineage verification.
- `NormalizedActivity`: The system's golden table schema mapping standard target volumes/weights, temporal windows, and snapshot conversion records.
- `ValidationIssue`: Non-blocking tracking tables detailing structural error alerts and operational exceptions linked to raw entries.
- `EmissionFactor`: Internal master reference index locking localized conversion coefficients.

## 3. Finite State Machine (Review Lifecycle)
- `PENDING`: Default initial registration state after running parsing logic.
- `SUSPICIOUS`: Automatic assignment condition if data streams trigger anomalous limits.
- `APPROVED`: Manual reviewer verification event. Emits a database-level save trap ensuring the calculation stays permanently immutable.
- `REJECTED`: Archived state removing anomalies from active processing view.

## 4. Absolute Scope Cuts (Do Not Build)
- No user authentication or permissions tables (Hardcode analytical email header context).
- No production-scale multi-tenancy relation models (Enforced via a flat string code tracker field).
- No asynchronous distributed engine workers (All computational conversions process inline).
- No exterior real-time emission factor API integrations.
- No third-party UI design framework dependencies or components.
