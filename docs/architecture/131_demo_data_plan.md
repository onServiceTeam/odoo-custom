# 131 — Demo Data Plan

> Script: `scripts/load_demo_data.py`
> Target DB: `onservice_test_db` (staging copy of prod)
> Last run: 2025-07-02 — all records created successfully

## Purpose

Provide realistic, non-trivial sample data so that the owner can open
the staging instance, click through the Operations menu, and see
populated lists, kanban boards, and form views that mirror real
onService daily operations.

---

## Data Created

### Customers (10 records)

| # | Name | Phone | Segment | City |
|---|------|-------|---------|------|
| 1 | Margaret Johnson | +1 (561) 555-0101 | new | Boca Raton |
| 2 | Robert Williams | +1 (561) 555-0102 | returning | Delray Beach |
| 3 | Patricia Davis | +1 (561) 555-0103 | at_risk | West Palm Beach |
| 4 | James Wilson | +1 (954) 555-0104 | premium | Fort Lauderdale |
| 5 | Linda Martinez | +1 (305) 555-0105 | new | Miami |
| 6 | David Anderson | +1 (561) 555-0106 | returning | Boynton Beach |
| 7 | Barbara Thomas | +1 (954) 555-0107 | new | Pompano Beach |
| 8 | Michael Garcia | +1 (786) 555-0108 | returning | Miami Beach |
| 9 | Susan Taylor | +1 (561) 555-0109 | at_risk | Lake Worth |
| 10 | Richard Brown | +1 (954) 555-0110 | premium | Coral Springs |

### Interactions (10 records)

Each customer has one interaction, covering multiple driver codes:

- `HACKED_POPUP_SCAM` (3×) — most common call-in reason
- `VIRUS_MALWARE` (2×)
- `SLOW_PERFORMANCE` (2×)
- `EMAIL_COMPROMISE` (1×)
- `PRINTER_ISSUE` (1×)
- `NETWORK_WIFI` (1×)

States: 7 classified, 2 new, 1 completed.
Session paths: session_now (5), callback (3), onsite_queue (1), session_scheduled (1).
Urgency: low (3), medium (4), high (3).

### CRM Leads (6 records)

| # | Type | Convertible? | Linked To |
|---|------|-------------|-----------|
| 1-3 | inquiry | No | Customers 1-3 (information-only callers) |
| 4-6 | convertible | Yes | Customers 4-6 (service-path interactions) |

### Cases (6 records)

| # | Customer | Stage | Driver |
|---|----------|-------|--------|
| 1 | Patricia Davis | repair_in_progress | VIRUS_MALWARE |
| 2 | James Wilson | billing_in_progress | HACKED_POPUP_SCAM |
| 3 | Linda Martinez | callback_scheduled | SLOW_PERFORMANCE |
| 4 | Robert Williams | closed_won (paid) | HACKED_POPUP_SCAM |
| 5 | David Anderson | online_session_started | EMAIL_COMPROMISE |
| 6 | Barbara Thomas | onsite_dispatched | NETWORK_WIFI |

### Billing Lines (on Cases 2 & 4)

- Case 2: STANDARD_FIX $129.99 + BROWSER_GUARD $49.99 = **$179.98**
- Case 4: ADVANCED_REPAIR $149.99 + DATA_BACKUP $79.99 = **$229.98**
  (payment_status = paid, payment_amount = $229.98)

### Customer Plans (2 records)

| Customer | Plan | Status | Months Left |
|----------|------|--------|-------------|
| James Wilson | PLAN_1YR | active | 8 months |
| Susan Taylor | PLAN_6MO | expiring_soon | < 30 days |

### Dispatch (1 record)

- Customer: Barbara Thomas
- Address: 700 E Atlantic Blvd, Pompano Beach FL 33060
- Status: `assigned` (advanced through draft → pending_approval → sent → has_applicants → assigned)
- Linked to Case 6

### Consent Records (5 records)

Various consent types (sms/marketing/email/recording/data_processing)
for different customers, some granted, some revoked.

---

## Script Design

```
scripts/load_demo_data.py
├── connect(db)           — XML-RPC connection
├── ref(model, domain)    — ID lookup helper
├── find_stage(code)      — Case stage by code
├── find_dispatch_status() — Dispatch status by code
├── find_driver(code)     — Call driver by code
├── find_product(code)    — Product variant by template code
└── load(db)              — Main orchestrator
```

**Safety:** The script is idempotent by design — re-running will create
duplicate partners (no unique constraint on demo names), but all
relational links are resolved at runtime.

**Usage:**
```bash
cd /home/onservice/odoo-custom
python3 scripts/load_demo_data.py                    # staging (default)
python3 scripts/load_demo_data.py onservice_prod_db  # production
```

## What The Owner Will See

| Menu | What's visible |
|------|---------------|
| Interactions | 10+ calls in list view, filterable by driver/urgency/state |
| Pipeline | 6 leads in kanban columns (inquiry vs convertible) |
| Cases | 6 cases across 5 different pipeline stages |
| Billing Queue | 2 cases with billing lines, 1 paid |
| Customer Plans | 2 plans — 1 active, 1 expiring soon in renewal queue |
| All Dispatches | 1 dispatch in "assigned" stage |
| Customers | 10 contacts with interaction counts |
| Consent Records | 5 records showing compliance tracking |
