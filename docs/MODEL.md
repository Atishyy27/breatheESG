# Architectural Data Model & Lineage Strategy

## Core Design Principles

The BreatheESG data model was designed to prioritize **auditability** and **idempotency** over simple CRUD operations. In corporate carbon accounting, the ability to trace a final CO₂e number back to its raw, immutable origin is a strict regulatory requirement.

### 1. Immutable Audit Trail (The Lineage Spine)
We implemented a strict three-tier lineage architecture:
`RawUpload` $\rightarrow$ `RawRecord` $\rightarrow$ `NormalizedActivity`

* **`RawRecord` is Immutable:** The original JSON string from the parsed file is stored exactly as received. If a normalization rule changes, or if an analyst deletes an activity, the raw evidence remains intact.
* **Foreign Key Protection:** `NormalizedActivity` maps to `RawRecord` via `models.PROTECT` or strict `CASCADE` rules ensuring orphaned emissions data cannot exist without source provenance.

### 2. Emission Factor Snapshotting
* **Decision:** We store `factor_value_used` and `emission_factor_source` directly on the `NormalizedActivity` table at the exact moment of calculation.
* **Why:** Emission factors (e.g., EPA, DEFRA) update annually. If we only stored a Foreign Key to a live `EmissionFactor` table, updating a factor in 2027 would silently alter historical 2026 reporting data, causing a critical audit failure. 

### 3. Verification State Machine
* **Decision:** Activity rows flow through a strict state machine: `PENDING` $\rightarrow$ `SUSPICIOUS` (if anomaly triggered) $\rightarrow$ `APPROVED`. 
* **Why:** We intentionally omitted a `LOCKED` state to reduce join overhead, treating `APPROVED` as the terminal state for this prototype.

### 4. Denormalized Facility Enrichment
* **Decision:** Facility locations are treated as loose strings (`facility_code`) mapped client-side, rather than strictly bound Foreign Keys to a `Facility` table.
* **Why:** Initial enterprise data ingestion is notoriously messy. Forcing strict referential integrity on plant codes during the upload phase would block processing for the entire file. We flag unmapped codes as `WARNING`s, allowing ingestion to complete while surfacing the gap to the analyst.