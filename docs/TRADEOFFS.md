# Deliberate Architectural Omissions

[cite_start]To maintain delivery velocity and prevent over-engineering, three explicit system omissions were enforced during the construction of this ingestion prototype.

## 1. Real-Time External API Synchronization
* [cite_start]**Why Omitted**: Integrating real-time connections for SAP Concur or Navan APIs requires substantial infrastructure overhead—including OAuth token refresh workflows, webhook management, rate-limiting backoffs, and complex retry mechanics[cite: 74]. [cite_start]Given that corporate carbon audits operate on predictable monthly or quarterly timelines, real-time sync adds unnecessary operational complexity for an MVP[cite: 60]. [cite_start]Batch file processing handles the required volume effectively[cite: 60].
* **Production Deployment Criteria**: This feature should be prioritized once the system is onboarding clients whose travel reporting groups manage over 1,000 global transactions per week.

## 2. Multi-Stage Authorization Approval Chains
* [cite_start]**Why Omitted**: Designing multi-user approval hierarchies (e.g., Analyst Entry $\rightarrow$ Manager Verification $\rightarrow$ Sustainability Lead Approval) requires complex role-based access control (RBAC), permission matrices, and automated email notification systems[cite: 82]. [cite_start]For a production prototype, focusing on a single, high-fidelity Analyst Workbench ensures the core data lineage remains clean and fully verifiable first[cite: 82].
* **Production Deployment Criteria**: Implement this feature when scaling the application for larger enterprise customers that require strict segregation of duties for compliance.

## 3. Calendar Operating-Day Prorating Weight Variations
* **Why Omitted**: The day-proportional utility billing split engine assumes a uniform energy load across the entire tracking window. It does not adjust calculations for non-operating business days, public holidays, or scheduled weekend plant shutdowns. Building calendar-aware weighting algorithms requires complex facility metadata schedules that are rarely available during initial data ingestion.
* **Production Deployment Criteria**: Introduce this level of precision when integrating direct IoT monitoring sub-meters across facilities that operate on highly variable or seasonal production schedules.