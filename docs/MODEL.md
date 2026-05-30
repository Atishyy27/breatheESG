# Data Model

## Design Intent

The model prioritises auditability over simplicity. Every CO₂e figure on the Audit Log must be traceable to an original file row. Approved records must be immutable. Emission factors used at calculation time must not change if the factor database is later updated.

---

## Entity Overview

```
RawUpload
  │  (one-to-many)
  ├── RawRecord  ←── ValidationIssue (many-to-one)
  │     │  (one-to-one or one-to-many)
  │     └── NormalizedActivity
  │
  └── (source_type, file_hash, status, uploaded_by_email)

EmissionFactor  (referenced at normalization time; value copied, FK not stored)
```

---

## Models

### `RawUpload`

Tracks a single file upload event.

| Field | Type | Notes |
|---|---|---|
| `source_type` | CharField | `SAP`, `UTILITY_BILL`, `UTILITY_METER`, `TRAVEL` |
| `filename` | CharField | Original filename as uploaded |
| `file_hash` | CharField | MD5 of file content. Checked on upload to prevent duplicate ingestion |
| `uploaded_by_email` | CharField | Read from `X-Analyst-Email` request header |
| `status` | CharField | `PROCESSING`, `COMPLETED`, `FAILED` |
| `total_rows` | IntegerField | Count of parsed rows |
| `normalized_rows` | IntegerField | Count of successfully created `NormalizedActivity` records |
| `error_rows` | IntegerField | Count of rows with blocking validation errors |
| `suspicious_rows` | IntegerField | Count of rows flagged `SUSPICIOUS` by anomaly rules |
| `processing_error` | TextField | Error message if pipeline crashes; empty on success |
| `uploaded_at` | DateTimeField | Auto-set on creation |

### `RawRecord`

Stores the original parsed content of a single file row, unchanged. Never modified after creation.

| Field | Type | Notes |
|---|---|---|
| `upload` | FK → RawUpload | `CASCADE` — deleting an upload removes its raw rows |
| `line_number` | IntegerField | 1-indexed position in the source file. Smart meter aggregated rows use offset ≥ 100000 to avoid collisions |
| `raw_data` | JSONField | The full parsed row as a dict. For CSV: `{header: value}`. For JSON: the original object |
| `has_error` | BooleanField | Set `True` if any `ValidationIssue` with `severity='ERROR'` exists for this record |

Uniqueness constraint: `(upload, line_number)`.

### `NormalizedActivity`

The primary analytical table. One record per emission event in the reporting system.

| Field | Type | Notes |
|---|---|---|
| `raw_record` | FK → RawRecord | Lineage back to source. `PROTECT` — cannot delete a raw record if an activity depends on it |
| `scope` | CharField | `SCOPE_1`, `SCOPE_2`, `SCOPE_3` |
| `scope_category` | CharField | GHG Protocol category string (e.g. `Category 1: Purchased Goods & Services`) |
| `activity_type` | CharField | Normalised activity slug: `fuel_diesel`, `electricity_grid`, `material_procurement`, `travel_flight`, `travel_hotel`, `travel_ground` |
| `activity_date` | DateField | The operational date of the emission event |
| `reporting_period` | CharField | `YYYY-MM` format. Derived from `activity_date`. Used for all time-series aggregation |
| `facility_code` | CharField, nullable | SAP plant code or utility `plant_ref`. Stored as a loose string; no FK constraint |
| `quantity` | DecimalField | Normalised quantity in canonical unit |
| `unit` | CharField | Canonical unit: `L`, `MT`, `kWh`, `pkm`, `room_nights`, `km` |
| `factor_value_used` | DecimalField | Emission factor kg CO₂e per unit, snapshotted at calculation time |
| `emission_factor_source` | CharField | Source label snapshotted at calculation time (e.g. `EPA 2025 Grid`) |
| `co2e_kg` | DecimalField | `quantity × factor_value_used`. The reported figure |
| `review_status` | CharField | State machine field — see below |
| `anomaly_code` | CharField, nullable | Machine-readable anomaly identifier |
| `anomaly_details` | TextField, nullable | Human-readable explanation shown to analyst |
| `reviewed_at` | DateTimeField, nullable | Set when status transitions to `APPROVED` or `REJECTED` |
| `reviewed_by_email` | CharField, nullable | Analyst email at time of review |
| `review_notes` | TextField | Required when `validation_bypassed=True` |
| `validation_bypassed` | BooleanField | `True` if analyst approved a record that had blocking validation errors |
| `source_metadata` | JSONField | Source-specific supplementary data preserved for audit (meter ID, vendor code, airport pair, etc.) |
| `created_at` | DateTimeField | Auto-set on creation |

### `ValidationIssue`

Non-blocking error and warning log. A record may have issues and still produce a `NormalizedActivity` (for warnings). Blocking errors (`severity='ERROR'`) set `RawRecord.has_error=True` and prevent normalization.

| Field | Type | Notes |
|---|---|---|
| `raw_record` | FK → RawRecord | `CASCADE` |
| `severity` | CharField | `ERROR` (blocks normalization) or `WARNING` (logged only) |
| `issue_type` | CharField | Machine-readable type: `MISSING_FIELD`, `NEGATIVE_VALUE`, `INVALID_DATE`, `INVALID_NUMBER`, `NEGATIVE_CONSUMPTION`, `MISSING_FACILITY`, `PROCESSING_CRASH` |
| `message` | TextField | Human-readable description for the analyst UI |

### `EmissionFactor`

Reference table seeded from `fixtures/emission_factors.json`. Factors are EPA, IEA, and DEFRA values.

| Field | Type | Notes |
|---|---|---|
| `activity_type` | CharField | Matches `NormalizedActivity.activity_type` |
| `unit` | CharField | The unit this factor applies to |
| `region` | CharField, nullable | Region qualifier (e.g. `IN` for India grid mix) |
| `factor_kg_co2e` | DecimalField | kg CO₂e per unit |
| `source` | CharField | Source label (e.g. `EPA 2025 Fuel Combustion`) |
| `valid_from` | DateField, nullable | Factor vintage year |

**The factor value is copied onto `NormalizedActivity.factor_value_used` at calculation time. `NormalizedActivity` does not store a FK to `EmissionFactor`.** This is intentional: if a factor is updated in 2027, it does not silently alter 2026 audit records.

---

## Review State Machine

```
         ┌─────────────────────────────────────────────────┐
         │                  PIPELINE CREATES                │
         │                       ↓                         │
         │                   PENDING                        │
         │             ↙           ↘                       │
         │     (anomaly            (no anomaly)            │
         │      detected)                                   │
         │         ↓                 ↓                      │
         │     SUSPICIOUS         PENDING                   │
         │         ↓                 ↓                      │
         │         └──────→  APPROVED (terminal)           │
         │         └──────→  REJECTED (terminal, archived) │
         └─────────────────────────────────────────────────┘
```

**`PENDING`** — Default state after normalization. Record awaits analyst review.

**`SUSPICIOUS`** — Set automatically by anomaly detection rules during or after normalization:
- `QUANTITY_SPIKE`: quantity exceeds 2.5× the facility's historical approved average for the same activity type
- `NO_EMISSION_FACTOR`: no `EmissionFactor` row found for the activity type/unit combination; CO₂e computed as zero
- `MISSING_FACILITY`: airport code not in the coordinate lookup table; flight distance unresolvable

**`APPROVED`** — Set by analyst or manager action. Sets `reviewed_at` and `reviewed_by_email`. Once approved, the `review_status` field cannot be changed — the view returns HTTP 409 on any further approve or reject call. This is the terminal audit-ready state.

**`REJECTED`** — Analyst dismissed the record. Archived in the database with rejection notes. Excluded from all dashboard aggregations. Kept for audit lineage.

---

## Source-of-Truth Tracking

Every `NormalizedActivity` traces back to a single `RawRecord`, which traces back to a single `RawUpload`. The `RawRecord.raw_data` JSON contains the original row exactly as parsed from the file. The `RawUpload` contains the filename, upload timestamp, uploader email, and file hash.

The export CSV includes `Source File` (the original filename) and `Reviewed By` (analyst email) columns, giving auditors the full chain: approved figure → emission factor used → raw row → source file.

---

## Scope Categorisation

Routing is determined at normalization time by the source processor, not inferred post-hoc.

| Source | Condition | Scope | Category |
|---|---|---|---|
| SAP | `MATNR` contains `DIESEL`, `FUEL`, `HFO`, `NATGAS`, `GAS`, `PETROL` | SCOPE_1 | Stationary Combustion |
| SAP | All other materials | SCOPE_3 | Category 1: Purchased Goods & Services |
| Utility Bill | Any | SCOPE_2 | Scope 2: Purchased Utilities |
| Smart Meter | Any | SCOPE_2 | Scope 2: Smart Meter Telemetry |
| Travel — flight | Any | SCOPE_3 | Category 6: Business Travel |
| Travel — hotel | Any | SCOPE_3 | Category 6: Business Travel |
| Travel — ground | Any | SCOPE_3 | Category 6: Business Travel |

---

## Unit Normalisation

SAP unit conversions applied inline at `process_sap_line` before factor lookup:

| Raw Unit (`MEINS`) | Canonical Unit | Conversion |
|---|---|---|
| `GAL` | `L` | × 3.78541 |
| `KG` | `MT` | ÷ 1000 |
| All others | Unchanged | — |

Travel distance is derived, not converted. If `origin` and `destination` are in the airport coordinate table, Haversine distance (km) is calculated and stored as `quantity` with `unit='pkm'`. If either code is absent, `quantity=0` and the record is flagged `SUSPICIOUS`.

---

## Multi-Tenancy

This prototype assumes a single client. The model has no `tenant_id` column.

A production implementation would add a `tenant` FK on `RawUpload`. All views, serializers, and aggregation queries would filter `raw_record__upload__tenant=request.tenant`. The `EmissionFactor` table may also need tenant-level overrides for clients with custom factor agreements.

This is not built because adding it mid-prototype requires a migration cascade across all five tables and row-level filtering across every query. The tradeoff is documented in `TRADEOFFS.md`.

---

## Audit Strategy

What an external auditor receives:
1. A CSV export containing all approved records with: reporting period, activity type, facility, quantity, unit, CO₂e (kg), factor value, factor source, reviewer email, review timestamp, source filename, bypass flag.
2. The ability to re-derive any CO₂e figure: `quantity × factor_value_used`.
3. A traceable filename that links back to the original upload record.

What is not provided in this prototype:
- No cryptographic signing of approved records.
- No row-level change log (Django signals would be needed to log individual field changes).
- No versioned emission factor history (factors are seeded once; updates are not tracked).