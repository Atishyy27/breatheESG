# Engineering Design Decisions

This document details the technical decisions and trade-offs made during the implementation of the BreatheESG ingestion pipeline prototype.

## 1. Ingestion Protocol: Flat-File Uploads vs. Live API Hooks
* [cite_start]**Decision**: All data integrations (SAP, Utilities, Travel) are routed through file-based ingestion streams rather than persistent live API connections[cite: 57].
* [cite_start]**Justification**: Real-world enterprise systems (specifically legacy SAP instances) rarely open direct, outbound OData or BAPI endpoints to third-party sustainability vendors without months of security clearance[cite: 58]. [cite_start]Financial and facility operations groups routinely manage data sharing via monthly batch flat-file extracts (e.g., transaction list dumps)[cite: 58, 59, 60]. [cite_start]Designing the core layer around file processing enables immediate customer onboarding without integration friction[cite: 60].

## 2. Temporal Normalization: Day-Proportional Billing Splits
* **Decision**: Utility billing periods that cross calendar month boundaries are programmatically prorated across separate rows based on individual day weights.
* **Justification**: Corporate accounting sheets require strict month-to-month carbon boundaries. If a commercial electricity invoice runs from April 12 to May 11, charging a single lump sum to a single month introduces significant data skew. Prorating consumption day-proportionally distributes carbon impacts precisely across correct financial tracking periods.

## 3. Scope Classifications and Mapping Parameters
* **Decision**: Source pipelines parse inputs directly into distinct, protocol-aligned categories:
    * SAP items containing fuel markers route directly to **Scope 1 (Stationary Combustion)**.
    * Utility portal and smart meter metrics route to **Scope 2 (Purchased Utilities)**.
    * Travel ledger arrays map to **Scope 3 (Category 6: Business Travel)**.
* **Justification**: This data model maps exactly to the Greenhouse Gas (GHG) Protocol Corporate Standard, matching heterogeneous business operations to their standard regulatory reporting brackets.

## 4. Flight Distance Approximations: Embedded Haversine Calculations
* **Decision**: Distances for air travel segments are derived using great-circle Haversine calculations mapped against a static core IATA airport database, rather than calling real-time flight path APIs.
* **Justification**: Corporate expense platforms rarely export actual flight paths or flight logs due to costs and access limitations—they provide simple routing strings (e.g., `BOM -> LHR`). Running local spherical geometry calculations provides a consistent, repeatable distance value with a predictable variance of 5–10%, bypassing the need for third-party network calls during ingestion.

## 5. Validation Enforcement: Error Log Blocking with Analyst Bypass
* **Decision**: Critical schema violations (such as missing quantities or negative values) block carbon calculations and mark the record as broken. However, analysts can check an override box to bypass these blocks if they append an explanatory review note.
* **Justification**: Real-world carbon data is messy, and automatic pipeline rejections can easily stall corporate workflows. Allowing analysts to force an override ensures processing continuity, while forcing a mandatory note provides a transparent change log for future sustainability auditors.