# Source Systems & Data Realism

This document outlines the research underlying the data parsers and the intentional edge cases injected into the sample datasets.

## 1. SAP Fuel & Procurement Data
* **Real-World Context:** Corporate SAP instances rarely expose direct OData APIs to third-party ESG platforms due to InfoSec policies. Data is typically exported via transaction `MB51` (Material Document List) or flattened via custom ABAP reports joining `MKPF` (Header) and `MSEG` (Line Items).
* **Injected Edge Cases:**
  * **Missing Quantities:** Blank `MENGE` fields trigger validation blocks.
  * **Unit Variation:** Mixed usage of `L` and `GAL` requires mathematical normalization before emission calculation.
  * **What Breaks in Production:** Our parser assumes a direct mapping. Real production systems require joining the `MARA` table for material descriptions and `T001W` for plant metadata.

## 2. Utility Electricity Billing
* **Real-World Context:** Facilities teams generally download monthly CSVs from regional utility portals (e.g., PG&E, Tata Power).
* **Injected Edge Cases:**
  * **Billing Period Misalignment:** Meters do not sync to calendar months. Our dataset includes periods like *April 12 to May 11*. The parser splits this using day-proportional weighting into two separate rows to ensure carbon accounting aligns with financial monthly close periods.
  * **Smart Meter IoT Intervals:** We included a high-frequency telemetry dataset to demonstrate batch aggregation of hourly kW/h reads into daily operational footprints.
  * **What Breaks in Production:** Day-proportional splits assume uniform 24/7 consumption. Production systems require facility operating-hour metadata to weight weekdays vs. weekends accurately.

## 3. Corporate Travel (Concur/Navan)
* **Real-World Context:** Expense platforms output Standard Accounting Extracts (SAE). Distance is almost never provided—only IATA airport codes.
* **Injected Edge Cases:**
  * **Geometric Enrichment:** Missing distances trigger an internal spherical Haversine calculation between airport coordinates.
  * **Cabin Class Multipliers:** Flights marked as "Business" apply a 2.5x spatial multiplier to base emissions.
  * **What Breaks in Production:** Our system assumes direct point-to-point flights. Real enterprise itineraries include multi-leg connections, and high-altitude radiative forcing multipliers (RFI) which vary by reporting framework.