# Manual Test Matrix

This document provides a step-by-step verification protocol for testing the ingestion pipeline, data transformations, and validation checks using the sample data files in `/sample_data`.

---

## 1. SAP Fuel & Procurement Validation Matrix
Verify these conditions by uploading `sap_fuel_procurement.csv` or inspecting rows via Django Admin.

| Scenario | Input Data Trigger | Pipeline Processing | Expected Database State |
| :--- | :--- | :--- | :--- |
| **Missing Quantity** | `MENGE` is empty or blank | Catches missing value; logs a blocking validation error | `RawRecord.has_error == True`<br>`ValidationIssue.severity == 'ERROR'`<br>*No NormalizedActivity is created.* |
| **Direct Fuel Routing** | `MATNR` contains `"FUEL_DIESEL"` | Identifies combustion fuel; routes to Scope 1 Stationary Combustion | `NormalizedActivity.scope == 'SCOPE_1'`<br>`NormalizedActivity.activity_type == 'fuel_diesel'` |
| **Procurement Routing** | `MATNR` contains `"STEEL_BEAMS"` | Identifies value chain material; routes to Scope 3 Category 1 | `NormalizedActivity.scope == 'SCOPE_3'`<br>`NormalizedActivity.activity_type == 'material_procurement'` |
| **German Date Parsing** | `BUDAT` is `"10.05.2026"` | Correctly parses European dot notation into standard date format | `NormalizedActivity.activity_date == 2026-05-10`<br>`NormalizedActivity.reporting_period == '2026-05'` |
| **Unit Normalization** | `MEINS` is `"GAL"` | Normalizes gallons into liters using the 3.78541 conversion factor | `NormalizedActivity.unit == 'L'`<br>`NormalizedActivity.quantity == input_menge * 3.78541` |

---

## 2. Utility Electricity Validation Matrix
Verify these conditions by uploading `utility_electricity_monthly.csv` or testing via the API.

| Scenario | Input Data Trigger | Pipeline Processing | Expected Database State |
| :--- | :--- | :--- | :--- |
| **Month Boundary Split** | `billing_start: 2026-04-12`<br>`billing_end: 2026-05-11` | Calculates day weights across the 30-day cycle. Generates two distinct rows prorated by days | Creates **2 separate** `NormalizedActivity` records pointing to the same `RawRecord`:<br>- Row 1: `reporting_period == '2026-04'` (19 days)<br>- Row 2: `reporting_period == '2026-05'` (11 days) |
| **Negative kWh Entry** | `consumption_kwh` is `< 0` (e.g., `-100`) | Identifies negative entry; logs a blocking validation error | `RawRecord.has_error == True`<br>`ValidationIssue.issue_type == 'NEGATIVE_CONSUMPTION'`<br>*No NormalizedActivity is created.* |
| **Unknown Plant Code** | `plant_ref` is empty or missing | Logs a non-blocking validation warning. Still generates activity row | `ValidationIssue.severity == 'WARNING'`<br>`NormalizedActivity.facility_code == None` |
| **Peak Demand Isolation** | Row includes `peak_demand_kw` | Stores demand metrics as structural metadata; excludes them from emissions calculations | `NormalizedActivity.source_metadata` contains `{"peak_demand_kw": "450.00"}`<br>*Emissions calculation uses consumption_kwh only.* |

---

## 3. Corporate Travel Validation Matrix
Verify these conditions by uploading `travel_expenses.json` or running target route lookups.

| Scenario | Input Data Trigger | Pipeline Processing | Expected Database State |
| :--- | :--- | :--- | :--- |
| **Distance Derivation** | `origin: "BOM"`, `destination: "LHR"` | Executes great-circle Haversine formula mapping core airport coordinates | `NormalizedActivity.unit == 'pkm'`<br>`NormalizedActivity.quantity == 7192.00` (Approximate km) |
| **Premium Class Scaling**| `booking_class` is `"Business"` | Snapshot lookup evaluates base emissions factor, then applies a 2.5x premium seating multiplier | `NormalizedActivity.co2e_kg == distance * factor * 2.5` |
| **Unmapped Airport Code**| `origin` or `destination` is `"XXX"` | Fails to resolve coordinates; flags row as suspicious instead of crashing the pipeline | `NormalizedActivity.review_status == 'SUSPICIOUS'`<br>`NormalizedActivity.anomaly_code == 'MISSING_FACILITY'`<br>`NormalizedActivity.quantity == 0.00` |
| **Alternative Travel Types**| `expense_type` matches hotel stay | (Future Expansion / Phase 2) Identifies non-flight travel types and routes to separate target calculation factors | Evaluated via dedicated hotel reference tables using `unit: room_nights` |
