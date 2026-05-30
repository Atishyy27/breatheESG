# Deliberate Omissions

Three things that were explicitly not built, and why.

---

## 1. Multi-Tenant Data Isolation

**What was omitted.** Every model in the system assumes a single client. There is no `Tenant` model, no `tenant_id` foreign key, and no row-level filtering by client in any query or serializer.

**Why omitted.** Adding multi-tenancy mid-prototype requires a migration cascade: a `Tenant` table, a FK on `RawUpload`, and a `WHERE tenant_id = ?` clause on every query in `views.py`, `processors.py`, and the serializers. Implementing it correctly also requires Django's ORM to enforce tenant context at the session layer rather than as an optional filter — otherwise, a query that forgets the filter leaks data across clients. That level of enforcement takes design time the prototype timeline did not have. Adding a `tenant` column and hoping every query remembers to filter it is worse than not building it at all, because it creates the appearance of isolation without the reality.

**What a production version would do.** Add a `Tenant` model with a `slug` identifier. Add `tenant = models.ForeignKey(Tenant, on_delete=models.PROTECT)` to `RawUpload`. All downstream models (`RawRecord`, `NormalizedActivity`) inherit tenant context through the FK chain. A custom DRF base class or middleware resolves the active tenant from the request and injects a queryset scope. All views inherit from this base and never call `.all()` without the tenant filter already applied at the manager level.

---

## 2. Real-Time API Integration with Source Systems

**What was omitted.** All three data sources — SAP, utility portals, and corporate travel platforms — are ingested via file upload. There are no live API connections, scheduled polling jobs, OAuth token management, or webhook receivers.

**Why omitted.** SAP does not expose direct API access to third-party vendors without enterprise IT involvement (RFC authorisation, SAP Gateway configuration, InfoSec review). Utility portals in India and most of the US have no public API — data is only available as a manual portal download. Concur and Navan do have APIs, but each requires OAuth 2.0 client credentials, sandbox access, and rate-limit handling. Building even one live API integration would have consumed most of the available prototype time while delivering no analytical value beyond what file upload already provides. Corporate carbon data is also inherently periodic — monthly or quarterly — so real-time sync adds no practical benefit for the reporting cycle.

**What a production version would do.** For SAP: a scheduled ABAP report configured in the client's SAP system that SFTPs a nightly flat file to an ingestion endpoint. For utility portals that offer APIs (Green Button standard in the US, some DISCOM APIs in India): a configurable polling job that fetches the latest billing period on a monthly schedule. For Concur/Navan: a webhook or scheduled export using the SAE API, triggered after each expense report approval cycle. Each source would have an idempotent ingestion job keyed on file hash or API record ID to prevent duplicate processing on re-delivery.

---

## 3. Calendar-Aware Utility Consumption Weighting

**What was omitted.** The utility billing period splitter distributes consumption evenly across days. A billing window from April 12 to May 11 assigns each of the 30 days an equal share of total kWh, regardless of whether those days are weekdays, weekends, or holidays.

**Why omitted.** Implementing calendar-aware weighting requires two things that are not available during initial client onboarding: a facility operating schedule (which hours of which days is the plant actually running) and a local public holiday calendar (which varies by state or country). Without these inputs, any weighting other than uniform is an assumption that could produce a less accurate split than the simple proportional approach. The uniform split is at least transparent and reproducible from the bill data alone.

**What a production version would do.** Each facility would have an associated operating schedule: `{weekday: 16h, saturday: 8h, sunday: 0h}`. The billing period splitter would weight each day's share by its operating hours relative to the period total. For large industrial customers, sub-meter data (already partially handled via the smart meter stream) is the correct long-term solution — hourly interval data eliminates the need for any estimation.