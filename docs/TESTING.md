# Operational Manual Verification Matrix

This suite profiles end-to-end processing execution matrices across structural and semantic edge cases.

| Core Target Vector | Processing Scenario | Input Exception Parameter | Expected Pipeline Behaviour | Verification Metric |
| :--- | :--- | :--- | :--- | :--- |
| **SAP Ingestion** | Missing Quantity | `MENGE` parameter field left blank | Emits Validation `ERROR` log block; halts processing before row normalization | `RawRecord.has_error == True` |
| **SAP Ingestion** | Stationary Fuel Classification | `MATNR` contains keyword `"FUEL_DIESEL"` | Routes allocation targets directly to Scope 1 (Stationary Combustion) | `NormalizedActivity.scope == "SCOPE_1"` |
| **SAP Ingestion** | Procurement Classification | `MATNR` contains keyword `"STEEL_BEAMS"` | Routes allocation targets directly to Scope 3 (Purchased Goods) | `NormalizedActivity.scope == "SCOPE_3"` |
| **SAP Ingestion** | German Format Dates | `BUDAT` formatted as `"10.05.2026"` | Parses string into structural system date index cleanly (`2026-05-10`) | `NormalizedActivity.reporting_period == "2026-05"` |
| **SAP Ingestion** | Non-Standard Weight Multipliers | `MEINS` volume unit marked as `"GAL"` | Normalizes row volume targets into standard Liters using a 3.78541 multiplier | `NormalizedActivity.unit == "L"` |
| **Utility Ingestion**| Temporal Month Cross Splitting | `billing_start: 2026-04-12`, `billing_end: 2026-05-11` | Day-proportionately splits consumption totals across individual month activity rows | 2 separate activities generated pointing back to 1 `RawRecord` |
| **Utility Ingestion**| Non-Emission Metadata Preservation | Inbound bill registers `peak_demand_kw: 450.00` | Excludes infrastructure demand from footprint calculations, preserving it inside JSON fields | `source_metadata` retains peak value |
| **Utility Ingestion**| Sub-Zero Consumption Failures | `consumption_kwh` registered as `-100.00` | Logs Validation `ERROR` condition block; prevents row normalization | Record flagged on upload summary metrics |
| **Travel Ingestion** | Geospatial Coordinate Derivation | JSON payload registers `origin: "BOM"`, `destination: "LHR"` | Runs an internal Haversine calculation to determine great-circle distance (~7200 km) | `NormalizedActivity.quantity` populated with km |
| **Travel Ingestion** | Seating Class Multiplier | `booking_class` designated as `"Business"` | Applies a 2.5x emissions scaling coefficient to passenger distance totals | `co2e_kg` reflects premium multiplier |
| **Travel Ingestion** | Unmapped Airport Exceptions | JSON payload tracks untracked code `"XXX"` | Normalizes row with 0 km and shifts the verification state to `SUSPICIOUS` | `anomaly_code == "MISSING_FACILITY"` |
| **Compliance Review**| Manual Analyst Overrides | Try approving row tracking active validation error | Blocks operation with a `400 Bad Request` unless override bypass check is passed with notes | API state transition rejected |
