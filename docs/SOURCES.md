# Source Systems

For each source: what format was researched, what was built, what the sample data looks like, and what would break in a real deployment.

---

## 1. SAP — Fuel & Material Procurement

### What the real format looks like

SAP tracks material movements in tables `MKPF` (goods movement header) and `MSEG` (goods movement line items). The standard way to extract this data without API access is transaction `MB51` (Material Document List), which produces a flat report joinable to `MARA` (material master) for descriptions and `T001W` (plant master) for facility names.

A typical flat-file export from MB51 contains these fields in the SAP technical column naming convention:

- `MBLNR` — Material document number
- `BUDAT` — Posting date (format: `DD.MM.YYYY` in European locale, `YYYY-MM-DD` in US locale)
- `WERKS` — Plant code (e.g. `IN01`, `DE02`)
- `MATNR` — Material number (e.g. `FUEL_DIESEL_HVO`, `STEEL_BEAMS_S355`)
- `MENGE` — Quantity
- `MEINS` — Unit of measure (`L`, `KG`, `MT`, `GAL`, `PC`)
- `LIFNR` — Vendor number
- `NETWR` — Net value
- `WAERS` — Currency

Real exports also include `BWART` (movement type: 101=goods receipt, 201=goods issue to cost center) which distinguishes consumption from receipts — this prototype ignores movement type and treats all records as consumption events.

### What was built

The parser reads CSV with the SAP technical column names above. Delimiter detection distinguishes pipe-separated exports from comma-separated ones. Date formats `DD.MM.YYYY`, `YYYY-MM-DD`, `DDMMYYYY`, and `YYYY/MM/DD` are all handled.

Material type is determined by keyword matching in `MATNR`:
- Contains `DIESEL`, `FUEL`, `PETROL`, `GAS`, `HFO`, `NATGAS`, `NATURAL_GAS` → Scope 1, `fuel_diesel`
- Everything else → Scope 3 Category 1, `material_procurement`

Unit normalization: `GAL` → `L` (×3.78541); `KG` → `MT` (÷1000). Other units pass through.

### Sample data shape

```csv
MBLNR,BUDAT,WERKS,MATNR,MENGE,MEINS,BWART,LIFNR,NETWR,WAERS
5000012340,15.02.2026,IN01,FUEL_DIESEL_B7,14818.99,L,201,VEND_0042,920345.00,INR
5000012341,06.03.2026,IN02,STEEL_BEAMS_S355,12071.44,MT,101,VEND_0017,4105290.00,INR
5000012342,04.04.2026,DE02,FUEL_HFO_180CST,8200.00,KG,201,VEND_0089,614200.00,EUR
```

Dates in European `DD.MM.YYYY` format. Plant codes are four characters: two-letter country code + two-digit number. Material numbers follow an internal naming convention that encodes the material type in a human-readable prefix.

### What would break in production

**Keyword matching is fragile.** `PROC_FUEL_CLEANING` matches `FUEL` but is a cleaning chemical, not a combustion fuel. A production parser requires a client-maintained material-to-category mapping table, likely drawn from the `MARA` material master or a sustainability team spreadsheet.

**Movement type is ignored.** A goods receipt (BWART=101) is a stock increase, not combustion. Processing it as consumption overstates emissions. Production requires filtering by movement type.

**Plant codes are arbitrary.** `IN01` means nothing without the plant master (`T001W`). The prototype maps known codes client-side. A production system needs the plant master loaded as a reference table to resolve codes to facility names and locations.

**German column headers.** SAP with German system language produces `Buchungsdatum` not `BUDAT`, `Materialnummer` not `MATNR`. Column name mapping would need to be configurable per client.

---

## 2. Utility — Electricity Billing

### What the real format looks like

Utility companies in India (Tata Power, CESC, MSEDCL) and the US (PG&E, ConEdison) offer monthly CSV exports from their customer web portals. The export typically contains:

- Account number and meter ID
- Billing start and end dates (often non-calendar-aligned)
- Total consumption in kWh
- Peak and off-peak split (where time-of-use tariffs apply)
- Peak demand in kW (billed separately from consumption)
- Tariff code
- Total charge in local currency

A separate format exists for advanced metering infrastructure (AMI) smart meters: 15-minute or hourly interval data with timestamp, interval kWh reading, and a data quality flag.

### What was built

**Monthly bills.** The parser reads CSV with fields `billing_start`, `billing_end`, `consumption_kwh` (or `peak_consumption_kwh` + `offpeak_consumption_kwh`), `plant_ref`, `meter_id`, `peak_demand_kw`. Billing period splitting across calendar months is handled by iterating day-by-day across the billing window and proportionally allocating kWh. Each calendar month in the billing period produces a separate `NormalizedActivity` row pointing to the same `RawRecord`.

**Smart meter intervals.** The parser reads hourly CSV with `timestamp` (format: `YYYY-MM-DD HH:MM:SS`, with optional timezone offset), `kwh_interval` (or `interval_kwh`), and `quality`. Timezone offsets are stripped before parsing. Rows with `quality=SUSPECT` are skipped. All valid hourly rows for a given calendar day are summed into a single daily total, which is written as one `NormalizedActivity` row.

### Sample data shape

Monthly bills:
```csv
meter_id,plant_ref,billing_start,billing_end,consumption_kwh,peak_consumption_kwh,offpeak_consumption_kwh,peak_demand_kw,tariff_code
MTR_DE02_01,DE02,2026-04-12,2026-05-11,31000,21700,9300,450.00,HV_TOU_A
MTR_IN01_02,IN01,2026-02-01,2026-03-02,18400,12880,5520,310.00,LV_FLAT_B
```

Smart meter intervals:
```csv
timestamp,meter_id,kwh_interval,quality,voltage_v
2026-06-01 00:00:00+05:30,MTR_IN01_01,2.34,GOOD,230.1
2026-06-01 01:00:00+05:30,MTR_IN01_01,1.98,GOOD,229.8
2026-06-01 02:00:00+05:30,MTR_IN01_01,0.41,SUSPECT,228.1
```

Billing periods deliberately cross month boundaries to exercise the splitting logic. The smart meter file includes timezone offsets and a SUSPECT reading to exercise those handling paths.

### What would break in production

**Uniform load assumption.** Day-proportional splitting treats every day as identical. A factory with weekend shutdowns has near-zero Saturday and Sunday consumption. Prorating by day count distributes weekend emissions that did not actually occur. Production requires a facility operating-hours calendar.

**Single emission factor for all regions.** The prototype uses one `electricity_grid` factor filtered by region `IN`. A multi-facility client with sites in Germany, India, and the US requires different grid emission factors per region. The factor lookup would need to match `plant_ref` to a region code.

**One meter per row assumption.** Some portal exports put multiple meters on the same row with separate columns. The parser assumes one meter per row.

**PDF bills are not handled.** Some facilities teams only have PDF bills. PDF parsing was explicitly out of scope for this prototype.

---

## 3. Corporate Travel — Flights, Hotels, Ground Transport

### What the real format looks like

Concur's Standard Accounting Extract (SAE) exports expense reports as structured data. The JSON or CSV export contains one row per expense line item. Each item has an expense type classifier and type-specific fields. Key fields across all types:

- `ExpenseType` / `expense_type` — category classifier
- `TransactionDate` / `transaction_date` — date of the expense
- `EmployeeID` / `employee_id` — traveller identifier
- `VendorName` / `vendor` — airline, hotel chain, car rental
- `ReportName` — expense report title

Flight-specific:
- `Origin`, `Destination` — IATA airport codes
- `ClassOfService` / `booking_class` — Economy, Business, First

Hotel-specific:
- `City` — destination city
- `NumberOfNights` / `nights`

Ground transport:
- `Distance` / `distance_km` (sometimes absent)
- `Mode` — Taxi, Train, Car Rental

Navan (formerly TripActions) exports use a similar flat structure. Both platforms rarely provide flight distance — only origin/destination codes.

### What was built

JSON records with the following shape per expense type:

Flight:
```json
{
  "expense_type": "Air Travel",
  "transaction_date": "2026-03-14",
  "employee_id": "EMP_4821",
  "origin": "BOM",
  "destination": "LHR",
  "booking_class": "Business",
  "vendor": "Air India"
}
```

Hotel:
```json
{
  "expense_type": "Hotel Stay",
  "transaction_date": "2026-03-15",
  "employee_id": "EMP_4821",
  "city": "London",
  "nights": 3,
  "vendor": "Hilton"
}
```

Ground transport:
```json
{
  "expense_type": "Ground Transport",
  "transaction_date": "2026-03-18",
  "employee_id": "EMP_4821",
  "mode": "Taxi",
  "distance_km": 42
}
```

Non-emission expense types (`Meals`, `Entertainment`, `Other`) are silently skipped.

Flight distance is calculated using the Haversine great-circle formula from a static table of 20 IATA airport coordinates covering the airports most commonly appearing in enterprise travel data for companies with Indian headquarters and European/US operations. Airports outside this set produce zero-distance records flagged `SUSPICIOUS` with `anomaly_code=MISSING_FACILITY`.

Business and First class bookings receive a 2.5× CO₂e multiplier applied to the base economy factor, per DEFRA's passenger aircraft emissions methodology.

### Sample data shape

The sample file `travel_itineraries.json` is an array of objects using the format above. Records are drawn from realistic travel patterns: India-to-UK long-haul, India domestic, short-haul European legs, ground transport to/from airports.

### What would break in production

**20-airport coordinate table.** Any route not in the hardcoded table produces a suspicious zero-distance record. A production system requires a full IATA database (7,000+ airports).

**Point-to-point only.** Multi-leg journeys (BOM → DXB → LHR on separate tickets) must be submitted as separate expense lines. A single record with two legs is not handled.

**No radiative forcing index (RFI).** High-altitude aviation emissions have a warming effect beyond CO₂ alone. DEFRA recommends an RFI multiplier of approximately 1.9× for total climate impact. This is not applied; the prototype uses CO₂-only factors. Some reporting frameworks require RFI; others do not.

**No distance field from platform.** If a future platform export includes `distance_km` on flight records, the Haversine calculation should be skipped and the provided value used. The processor does not check for a pre-supplied distance.