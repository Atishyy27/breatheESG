# BreatheESG

A Django + React prototype for ingesting, normalizing, and reviewing corporate emissions data from three enterprise source types. Built as a four-day technical assignment for Breathe ESG.

**Live app:** https://breatheesg-gg71.onrender.com/
**Note:** Deployed on Render free tier. First load may take 30–60 seconds while the dyno wakes.

---

## Problem Statement

Enterprise carbon accounting has a data collection problem. Every client keeps emissions data in a different place and shape: SAP exports for fuel and materials procurement, CSV downloads from utility portals for electricity, JSON exports from travel platforms for flights and hotels. None of these sources use the same units, date formats, field names, or boundary definitions.

The hard part is not the CO₂e math. It is getting heterogeneous, messy source data into a single normalized schema that auditors can trust — with a clear chain of evidence from final approved number back to the original raw file.

---

## What This Prototype Does

**Ingest.** Accepts file uploads from three source types: SAP flat-file exports (CSV), utility billing exports (CSV), and corporate travel expense exports (JSON). Files are parsed, each row stored as an immutable raw record, and the full file hash is checked against prior uploads to prevent duplicate ingestion.

**Normalize.** Each raw record is processed by a source-specific pipeline that maps it into a standard `NormalizedActivity` schema: scope classification (Scope 1/2/3), activity type, quantity in a canonical unit, reporting period, and CO₂e computed from a snapshotted emission factor. Billing periods that cross calendar month boundaries are split day-proportionally into separate rows. Flight distances are calculated from IATA airport codes using Haversine geometry when the source data provides no distance.

**Review.** Normalized records enter a queue with status `PENDING` or `SUSPICIOUS`. Suspicious records are flagged automatically by anomaly rules: quantity spikes, unresolvable airport codes, zero-emission computations when quantity is nonzero. Analysts can inspect the full detail of any record, including its original raw data, all validation issues, and the emission factor used.

**Approve.** Analysts or managers select records individually or in batch and approve them for audit. Approval sets `reviewed_by_email`, `reviewed_at`, and locks the record. Validation errors can be bypassed with a mandatory written justification that is stored on the record.

**Audit.** The Audit Log shows all approved records in an immutable ledger. The export endpoint produces a CSV with Scope, CO₂e, factor source, reviewer name, and timestamp — the minimal set an external auditor needs to verify a reported figure.

---

## Supported Sources

### SAP Fuel & Procurement (CSV)

Modelled on the flat-file output of SAP transaction `MB51` (Material Document List), which joins `MKPF` header and `MSEG` line item tables. Field names follow SAP's standard technical names: `MENGE` (quantity), `MEINS` (unit of measure), `MATNR` (material number), `BUDAT` (document date), `WERKS` (plant code), `LIFNR` (vendor), `NETWR` (net value).

Material type determines scope routing: records whose `MATNR` contains fuel keywords (`DIESEL`, `FUEL`, `HFO`, `NATGAS`) route to Scope 1 stationary combustion. All other materials route to Scope 3 Category 1 (purchased goods and services).

Units `GAL` and `KG` are normalized at ingestion: gallons convert to litres (×3.78541), kilograms convert to metric tonnes (÷1000).

### Utility Electricity Billing (CSV)

Modelled on the monthly summary CSV export available from regional utility portals (e.g., Tata Power, PG&E). Key fields: `billing_start`, `billing_end`, `consumption_kwh`, `plant_ref`, `meter_id`, `peak_demand_kw`.

A separate smart meter stream accepts hourly interval CSV data with `timestamp` and `kwh_interval` columns. Hourly rows are aggregated into daily totals before normalization, with `SUSPECT`-quality readings skipped.

Billing periods that cross calendar month boundaries are split proportionally: a bill covering April 12–May 11 produces two `NormalizedActivity` rows, one for April (19 days) and one for May (11 days), each with the proportional share of kWh and CO₂e.

### Corporate Travel (JSON)

Modelled on the Concur Standard Accounting Extract (SAE). Each record is a JSON object with fields `expense_type`, `origin`, `destination`, `booking_class`, `transaction_date`, `employee_id`, `vendor`, `nights` (hotels), `distance_km` (ground), `city`.

Three expense subtypes are handled: flights, hotel stays, and ground transport. Flight CO₂e is calculated from great-circle distance (Haversine from a static IATA coordinate table) multiplied by a per-km emission factor. Business or first class bookings apply a 2.5× multiplier per DEFRA floor-space methodology. Hotel stays use a per-room-night factor. Ground transport uses a per-km factor.

---

## Workflow

```
Upload file (SAP CSV / Utility CSV / Travel JSON)
↓
Parse rows — delimiter detection, Excel formula stripping, duplicate file hash check
↓
Validate — check required fields, reject negatives and invalid dates, warn on missing facility
↓
Normalize — scope routing, unit conversion, Haversine enrichment, billing period splitting
↓
Anomaly detection — quantity spike detection against facility historical average
↓
Review Queue — analyst inspects PENDING and SUSPICIOUS records
↓
Approve (single or batch) — reviewer email and timestamp locked on record
↓
Audit Log — immutable ledger of approved records, exportable as CSV
```

---

## Tech Stack

### Backend
- Python 3.12, Django 5.x, Django REST Framework
- SQLite (local and deployed — ephemeral on Render free tier)
- No Celery or async workers; all processing runs inline per upload

### Frontend
- React 18, TypeScript, Vite
- Recharts for all charts
- Tailwind CSS + shadcn/ui components
- Served as static files by WhiteNoise from Django

### Deployment
- Render (single web service, monolith)
- Frontend built with Vite, static files collected into Django's `staticfiles/` directory and served via WhiteNoise

---

## Repository Structure

```
breatheESG/
├── backend/
│   ├── breathe/                ← Django project: settings, urls, wsgi
│   ├── ingestion/              ← Core application
│   │   ├── models.py           ← RawUpload, RawRecord, NormalizedActivity,
│   │   │                         ValidationIssue, EmissionFactor
│   │   ├── views.py            ← All REST endpoints
│   │   ├── processors.py       ← Per-source normalization logic
│   │   ├── validation.py       ← Pre-normalization field validation
│   │   ├── serializers.py      ← DRF serializers for API responses
│   │   ├── enrichment.py       ← Post-normalization enrichment hooks
│   │   └── fixtures/
│   │       └── emission_factors.json   ← EPA/IEA/DEFRA factor seed data
│   ├── sample_data/            ← Ready-to-upload test files
│   │   ├── sap_procurement.csv
│   │   ├── sap_fuel_procurement.csv
│   │   ├── utility_bills.csv
│   │   ├── utility_intervals.csv
│   │   ├── travel_expenses.json
│   │   ├── travel_itineraries.json
│   │   └── clean/ corrupted/ duplicate_uploads/ stress_test/
│   └── scripts/generators/     ← Parametric data generation scripts
│       ├── sap/
│       ├── utility/
│       ├── travel/
│       └── core/               ← Shared: anomaly injection, temporal patterns
├── frontend/
│   └── src/
│       ├── pages/              ← DashboardPage, ReviewQueuePage, AuditPage,
│       │                         AnalyticsPage, UploadsPage, RoleSelectPage
│       ├── components/         ← Layout shell, review modals, shared primitives
│       ├── hooks/              ← Data-fetching hooks (useDashboard, useReviewQueue, …)
│       ├── context/            ← RoleContext (role stored in localStorage)
│       └── lib/                ← api.ts, constants, utils
└── docs/
    ├── MODEL.md
    ├── DECISIONS.md
    ├── SOURCES.md
    └── TRADEOFFS.md
```

---

## Local Setup

### Prerequisites
- Python 3.12+
- Node 18+

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

python manage.py migrate
python manage.py loaddata ingestion/fixtures/emission_factors.json
python manage.py runserver
```

API available at `http://localhost:8000`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

App available at `http://localhost:5173`. The Vite dev server proxies `/api/` to `localhost:8000`.

### Environment variables

No `.env` file is required for local development. The Django settings use `DEBUG=True` and `ALLOWED_HOSTS=['*']` locally. For production, `SECRET_KEY` and `ALLOWED_HOSTS` are set as Render environment variables.

---

## Demo Flow

Select **Sustainability Manager** role on the role picker screen.

1. **Data Operations** — Upload `sample_data/sap_procurement.csv` with source type "SAP Material Movements Export". Observe the pass/warn/err counts in the historical register. Note the FAILED row for the smart meter file: this is a documented scope limitation (hourly telemetry format is handled as a separate stream type and must be uploaded under "Smart Meter Telemetry Stream").

2. **Data Operations** — Upload `sample_data/utility_bills.csv` with source type "Utility Portal Summary Bills". Upload `sample_data/travel_itineraries.json` with source type "Concur Routine Expenses JSON".

3. **Verification Queue** — Filter to "Anomalies Only". Click any `material_procurement` row to open the detail modal. The anomaly reason reads: no emission factor mapped for this activity type, CO₂e computed as zero, manual review required.

4. **Verification Queue** — Select five PENDING rows. Click "Approve Selected". Confirm the modal. Rows disappear from the queue.

5. **Audit Log** — Approved records appear in the Approved Emissions Ledger with "Locked" status and reviewer timestamp. Click "Export Ledger" to download the CSV.

6. **Analytics** — The "Review Pipeline by Source Type" chart shows three bars: SAP, UTILITY BILL, TRAVEL. The cumulative scope area chart shows Scope 1 (fuel), Scope 2 (electricity), and Scope 3 (procurement, travel) trends over time.

7. Switch to **Chief Financial Officer** role. The Executive Dashboard shows the aggregate carbon load KPI, scope apportionment donut, top emitters by facility, and pipeline health funnel.

8. Switch to **External Auditor** role. The Approve button is absent from the Verification Queue. The Audit Log and export are accessible. No upload or approval actions are available.

---

## Known Limitations

**SQLite on Render is ephemeral.** The free tier spins down after inactivity and wipes the filesystem on restart. Data uploaded to the live app may not persist across sessions. Load the sample data fresh at the start of a review session.

**No real authentication.** Role selection is stored in `localStorage`. The backend reads role from the `X-User-Role` request header. Any client can send any role header. This is documented as a deliberate prototype scope cut.

**SAP field names are English.** Real SAP exports may use German column headers depending on system locale settings. The parser handles the standard English technical names (`MENGE`, `MATNR`, `BUDAT`). A production deployment would need locale detection or a configurable column mapping layer.

**Airport coordinate table covers 20 airports.** Haversine calculations fail gracefully for airport codes outside the static lookup table — the record is created with zero distance and flagged SUSPICIOUS. A production system would use a full IATA database.

**Day-proportional utility splits assume uniform load.** A billing period split across months distributes kWh evenly per day. Production accuracy requires facility operating-hours metadata.

**Multi-tenancy is not implemented.** The current model assumes a single client. Tenant isolation would require a `tenant_id` foreign key on `RawUpload` with row-level filtering on all downstream queries.

---