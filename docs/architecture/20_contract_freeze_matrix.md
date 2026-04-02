# 20 — Contract Freeze Matrix

**Date:** 2026-05-31  
**Purpose:** Lock the data contracts between legacy middleware and Odoo models before building cases, billing, or telephony modules.  
**Methodology:** Every row is proved from code, schema, or current Odoo module behavior. No hand-waving.

---

## Legend

| Column | Meaning |
|--------|---------|
| **Legacy Table** | PostgreSQL table name in middleware (`script-secure-guard-8285b830`) |
| **Odoo Model** | Target `/mnt/extra-addons` model or stock model |
| **Status** | `BUILT` = model exists with tests · `PLANNED` = spec in doc 11 · `STOCK` = Odoo ships it · `NOT STARTED` = no spec |
| **Source-of-Truth** | Which system owns the canonical record during coexistence |
| **Invariants** | Rules that MUST hold for data integrity |

---

## 1. Submissions → ons.interaction

| Aspect | Legacy (submissions) | Odoo (ons.interaction) | Status |
|--------|---------------------|----------------------|--------|
| **PK** | `id` UUID | `id` serial (Odoo ORM) | BUILT |
| **Dedup key** | `cdr_primary_id` (TEXT, unique from call_logs linkage) | `threecx_cdr_id` (Char, UniqueIndex WHERE NOT NULL) | BUILT — verified in [interaction.py](../../addons/ons_ops_intake/models/interaction.py#L148) |
| **Customer link** | `linked_customer_id` UUID FK → customer_profiles | `partner_id` Many2one → res.partner | BUILT |
| **Agent attribution** | `submitted_by`, `phone_tech_id`, `assisting_tech_id`, `billing_tech_id` (all UUID FK → app_users) | `agent_id`, `assisting_agent_id`, `billing_agent_id` (all Many2one → res.users) | BUILT — `submitted_by` deliberately not modeled; `agent_id` = `phone_tech_id` |
| **Driver code** | `primary_driver_code` TEXT (not FK) | `primary_driver_id` Many2one → ons.call.driver | BUILT — stronger: relational FK instead of loose TEXT |
| **Secondary drivers** | `secondary_driver_codes` TEXT[] | `secondary_driver_ids` Many2many → ons.call.driver | BUILT |
| **Status fields** | `repair_status`, `payment_status`, `callback_status`, `call_status` (separate enums) | `state` selection: new/classified/assigned/completed | **GAP**: Interaction state is a lifecycle state. Repair/payment/callback statuses will live on `ons.case` and `ons.session` (not yet built) |
| **Session path** | `session_path` ENUM (NO_SESSION, SESSION_NOW, CALLBACK, ONSITE_QUEUE, NOT_APPLICABLE, SESSION_SCHEDULED) | `session_path` Selection (identical values, lowercased) | BUILT |
| **Financial** | `amount`, `service_purchased`, `is_subscription`, `base_product_type` | Not on interaction | **CORRECT**: Financial fields belong on `ons.session` / `account.move`, NOT on the intake record |
| **Call data** | `call_duration`, `talk_duration` via linked call_logs | `call_duration`, `talk_duration` Integer fields directly on interaction | BUILT |
| **Transcript** | `transcript`, `transcript_status` on call_logs | `transcript`, `transcript_status` directly on interaction | BUILT |
| **Timestamps** | `created_at`, `updated_at` | `create_date`, `write_date` (Odoo automatic) | BUILT |

### Invariants — ons.interaction
1. Every interaction MUST have `interaction_type` and `direction` (enforced: required=True)
2. `threecx_cdr_id` is unique when set (enforced: UniqueIndex)
3. `name` auto-generated via ir.sequence `ons.interaction` (enforced in create())
4. State machine: new → classified → assigned → completed (enforced in action methods via filtered())
5. `partner_id` resolution is explicit action, not automatic (by design — avoids false matches)

### Source-of-Truth during coexistence
- **Middleware** remains source of truth for submissions until 3CX daemon pushes directly to Odoo
- **Odoo** is source of truth for partner resolution and driver classification

---

## 2. call_logs → ons.interaction (merged)

| Aspect | Legacy (call_logs) | Odoo (ons.interaction) | Status |
|--------|-------------------|----------------------|--------|
| **PK** | `id` UUID | `id` serial | BUILT |
| **3CX CDR** | `cdr_primary_id` TEXT UNIQUE | `threecx_cdr_id` Char (UniqueIndex) | BUILT |
| **Caller/Callee** | `caller_number`, `callee_number`, `customer_number` | `customer_phone` (raw) | BUILT — single field; callee not separately tracked |
| **Normalized phone** | `phone_number_normalized` (digits only, indexed) | Not stored — normalized on-the-fly in `action_resolve_customer()` | **GAP**: Should consider stored computed field for phone matching performance |
| **Direction** | `direction` TEXT | `direction` Selection | BUILT |
| **Disposition** | `disposition` TEXT (answered, completed, missed, transferred, etc.) | `disposition` Selection (answered, missed, abandoned, voicemail, no_answer) | BUILT — slightly different values: legacy has "completed"/"transferred"; Odoo has "abandoned"/"voicemail" |
| **Recording** | `has_recording`, `recording_url`, `recording_direct_url` | `has_recording`, `recording_url` | BUILT — `recording_direct_url` not needed (single URL sufficient) |
| **Timing** | `call_start`, `call_end`, `call_duration`, `ring_duration`, `hold_duration`, `talk_duration`, `wait_duration` | `call_start`, `call_end`, `call_duration`, `talk_duration` | BUILT — `ring_duration`, `hold_duration`, `wait_duration` not modeled (low priority; can be added to metadata if needed) |
| **Agent** | `agent_extension`, `agent_id` FK | `agent_id` Many2one → res.users | BUILT — agent_extension not stored (3CX queue mapping via separate 3CX module later) |
| **Linking** | `submission_id`, `service_session_id`, `case_id`, `customer_id`, `contact_id` | `partner_id`, `lead_id` (case_id planned for ons_ops_cases) | PARTIAL — session_id and case_id TBD |

### Design Decision: Merge submissions + call_logs into ons.interaction
- **Rationale**: In legacy, submissions and call_logs are often 1:1 for phone interactions. The middleware's `linked_call_id` on submissions and `submission_id` on call_logs create a bidirectional link. Odoo merges these into a single record.
- **Exception**: A call_log with no submission (e.g., missed call, internal call) still creates an interaction record with `disposition=missed` and no classification data.

---

## 3. customer_profiles → res.partner (extended)

| Aspect | Legacy (customer_profiles) | Odoo (res.partner + ons_ops_intake) | Status |
|--------|--------------------------|--------------------------------------|--------|
| **PK** | `id` UUID | `id` serial | BUILT (stock) |
| **Name** | `first_name`, `last_name`, `full_name` (generated) | `name` (single field, stock) | BUILT — Odoo stores single name |
| **Phone** | `phone` (original), `phone_clean` (normalized) | `phone` (stock), `phone_sanitized` (computed by phone_validation) | BUILT — Odoo's phone_validation module handles normalization to E.164 |
| **Alternate phone** | `alternate_phone` | `mobile` (stock res.partner field) | STOCK |
| **Email** | `email` | `email` (stock) | STOCK |
| **Address** | `address_1`, `address_2`, `city`, `state`, `zip_postal`, `country` | `street`, `street2`, `city`, `state_id`, `zip`, `country_id` (stock) | STOCK |
| **Classification** | `customer_type`, `customer_segment`, `subscription_status` | `customer_segment`, `subscription_status` (custom), `customer_type` on interaction | BUILT — customer_type is per-interaction, not per-partner (correct: a business user can call about home stuff) |
| **Lifetime stats** | `lifetime_value`, `total_orders`, `total_cases`, `total_sessions`, `total_spent` | `lifetime_value` (custom), `interaction_count` (computed) | PARTIAL — `total_orders`, `total_cases`, `total_sessions`, `total_spent` will be computed from `ons.case` and `account.move` (not built yet) |
| **Odoo sync** | `odoo_partner_id`, `odoo_partner_name` | Native — res.partner IS the record | N/A — no sync needed when Odoo is the master |

### Invariants — res.partner (custom extensions)
1. `customer_segment` enum: new / returning / subscriber / vip (matches legacy)
2. `subscription_status` enum: none / active / cancelled / expired (matches legacy)
3. `lifetime_value` default 0.0 (matches legacy DEFAULT 0)
4. `interaction_count` is a real-time computed field, not denormalized (differs from legacy which denormalizes counts)

### Source-of-Truth during coexistence
- **Odoo res.partner** is already the customer master (legacy has `odoo_partner_id` FK pointing here)
- Partner creation/update flows FROM Odoo TO middleware (not reverse)

---

## 4. payment_transactions → account.move / account.payment

| Aspect | Legacy (payment_transactions) | Odoo Target | Status |
|--------|------------------------------|-------------|--------|
| **Model** | `payment_transactions` (flat table) | `account.move` (invoice) + `account.payment` (payment) | PLANNED in doc 15 — ons_ops_billing module |
| **Revenue source** | THE source of truth | `account.move` confirmed amounts | NOT STARTED |
| **Multi-source** | `source`: stripe, zoho_books, zoho_payments, odoo, manual | Odoo journal entries + payment provider bridges | NOT STARTED |
| **Agent attribution** | `processed_by`, `billing_agent_role`, `conversion_agent_role` | Will go on `ons.session` or custom `ons.conversion.attribution` model | NOT STARTED |
| **Conflict resolution** | `has_conflict`, `conflict_details`, `needs_manual_review`, `confidence_score` | No Odoo equivalent yet | NOT STARTED |

### Invariants (to enforce when built)
1. Every paid interaction MUST have a linked `account.move` with state=posted
2. Agent attribution must track intake/fixing/billing credit split (3 agents per conversion)
3. Refunds must be linked to original payment (not standalone)
4. Payment source tracking preserved for audit trail

---

## 5. callbacks → mail.activity / ons.case (TBD)

| Aspect | Legacy (callbacks) | Odoo Target | Status |
|--------|-------------------|-------------|--------|
| **Model** | `callbacks` (dedicated table with 30+ fields) | `mail.activity` (stock, scheduled actions) OR dedicated model within `ons_ops_cases` | PLANNED — decision pending |
| **Scheduling** | `callback_time`, `preferred_callback_time`, `timezone` | `mail.activity.date_deadline` OR `ons.callback.scheduled_datetime` | NOT STARTED |
| **Escalation** | Auto-escalate overdue to urgent | Odoo `mail.activity` has no auto-escalation | **GAP**: Need custom cron or dedicated model |
| **Auto-archive** | 7-day auto-archive on abandoned callbacks | Odoo has no equivalent | **GAP**: Need custom cron |
| **Assignment** | `assigned_to` UUID FK → app_users | `user_id` on activity or case record | NOT STARTED |
| **Priority** | low / normal / high / urgent | `mail.activity` has no priority field | **GAP**: Confirms need for custom model, not stock activity |

### Decision Required (for Prompt 4+)
- **Option A**: Use `mail.activity` with custom fields via inheritance → simpler, OCA-friendly
- **Option B**: Create `ons.callback` model → more complete, matches legacy exactly
- **Recommendation**: Option B — legacy callbacks have too many fields for stock activity

---

## 6. call_driver_codes → ons.call.driver

| Aspect | Legacy (call_driver_codes) | Odoo (ons.call.driver) | Status |
|--------|--------------------------|----------------------|--------|
| **PK** | `id` UUID | `id` serial | BUILT |
| **Code** | `code` TEXT UNIQUE NOT NULL | `code` Char (UniqueIndex) | BUILT |
| **Category** | `category_id` UUID FK → call_driver_categories (separate table) | `category` Selection (20 values) | BUILT — **TRADE-OFF**: Selection is simpler than M2O; categories are static in practice |
| **QA Rubric** | `qa_rubric_id` UUID FK → qa_rubrics | Not modeled | CORRECT — belongs in `ons_ops_ai` module (not built yet) |
| **Detection** | `common_phrases`, `detection_keywords`, `example_descriptions` | `common_phrases`, `detection_keywords` (Text fields) | BUILT — `example_descriptions` folded into `description` |
| **Flags** | `requires_callback`, `requires_onsite`, `is_upsell_opportunity` | All three present as Boolean | BUILT |
| **Priority** | `coaching_priority` TEXT | `coaching_priority` Selection | BUILT |
| **Usage** | `usage_count`, `last_used_at` | `interaction_count` (computed live) | BUILT — better: real-time computed instead of denormalized counter |

### Invariants — ons.call.driver
1. `code` is unique (UniqueIndex enforced)
2. 30 seed records loaded via `ons_call_driver_data.xml`
3. All 7 categories from legacy covered: Boot & Startup, Security, Performance, Network, Printer, Email, Account + Billing

---

## 7. qa_evaluations → ons.qa.evaluation (PLANNED)

| Aspect | Legacy (qa_evaluations) | Odoo Target | Status |
|--------|------------------------|-------------|--------|
| **Model** | `qa_evaluations` | `ons.qa.evaluation` (doc 11) | NOT STARTED — belongs in `ons_ops_ai` |
| **Linking** | call_log_id, submission_id, agent_id, rubric_id | interaction_id, agent_id, rubric_id | NOT STARTED |
| **Scoring** | total_score, max_score, percentage, section_scores JSONB | TBD — likely similar fields | NOT STARTED |

---

## 8. workmarket_assignments → ons.dispatch (PLANNED)

| Aspect | Legacy (workmarket_assignments) | Odoo Target | Status |
|--------|-------------------------------|-------------|--------|
| **Model** | `workmarket_assignments` | `ons.dispatch` (doc 11) | NOT STARTED — belongs in `ons_ops_dispatch` |
| **Linking** | submission_id FK | case_id + session_id (via ons.case) | NOT STARTED |
| **Location** | address, city, state, zip | partner address (related) + override fields | NOT STARTED |

---

## 9. jobs → ons.session (merged with service_sessions)

| Aspect | Legacy (jobs table) | Odoo Target | Status |
|--------|-------------------|-------------|--------|
| **Purpose** | Tracks assisting technician work separately | `ons.session` subsumes jobs + service_sessions | PLANNED in doc 11 |
| **Repair status** | pending → assigned → in_progress → completed → escalated → cancelled | `ons.session.pipeline_stage` | NOT STARTED |
| **Billing** | `is_billable`, `billing_status` | `payment_collected` Boolean + linked `account.move` | NOT STARTED |
| **SLA** | `due_at`, `sla_breach_at` | `sla_due_date` on `ons.case` | NOT STARTED |

### Design Decision: Merge jobs + service_sessions → ons.session
- Legacy has both `jobs` (per-agent repair task) and `service_sessions` (per-customer session). In practice they are 1:1.
- `ons.session` combines both: it tracks the session timeline AND the repair work within it.
- If multiple agents work one session, `assisting_agent_id` handles handoff. No need for separate jobs table.

---

## 10. inbox_messages → mail.message (stock)

| Aspect | Legacy (inbox_messages) | Odoo Target | Status |
|--------|------------------------|-------------|--------|
| **Model** | `inbox_messages` (custom email queue) | `mail.message` + `mail.mail` (stock Odoo) | STOCK — Odoo handles email natively |
| **Thread linking** | `submission_id`, `customer_id`, `dispatch_id` | `res_id` + `model` on mail.message (polymorphic) | STOCK |
| **Folders** | inbox, sent, drafts, trash, archive, spam | Odoo has status flags (is_internal, needaction, starred) | **SEMANTIC GAP** — Odoo doesn't have folder model. Use `mail.message` subtype + custom filters |
| **Shared inbox** | `inbox_account_id` FK → shared_inbox_accounts | `mail.alias` + `fetchmail.server` (stock) | STOCK — may need custom shared inbox UI in `ons_ops_comms` |

---

## 11. realtime_call_sessions / realtime_agent_status → ons_ops_3cx (PLANNED)

| Aspect | Legacy | Odoo Target | Status |
|--------|--------|-------------|--------|
| **Model** | `realtime_call_sessions`, `realtime_agent_status_slices` | `ons.threecx.queue`, `ons.threecx.agent` (doc 12) | NOT STARTED — `ons_ops_3cx` module |
| **Update freq** | 30-second polling | Daemon pushes to Odoo via JSON-RPC (doc 15) | NOT STARTED |

---

## 12. Pipeline Stages / Enums Crosswalk

| Legacy Enum | Legacy Values | Odoo Mapping | Match? |
|-------------|--------------|-------------|--------|
| repair_status | pending, assigned, in_progress, on_hold, completed, escalated, cancelled | `ons.session.pipeline_stage` (NOT BUILT) | PLANNED |
| payment_status | pending, paid, for_collection, refunded, disputed, cancelled | `account.move.payment_state` (stock: not_paid, in_payment, paid, partial, reversed) | **SEMANTIC GAP** — `for_collection` has no stock equivalent; need custom field or activity |
| callback_status | pending, scheduled, completed, cancelled, no_answer, archived | `ons.callback` model (NOT BUILT) | PLANNED |
| call_status | answered, missed, declined, transferred | `ons.interaction.disposition` (answered, missed, abandoned, voicemail, no_answer) | PARTIAL — "transferred" not in current Selection; "declined" → "no_answer" |
| direction | inbound, outbound, internal | `ons.interaction.direction` — identical values | MATCH |
| caller_type | first_time_caller (→new), returning_caller (→returning), subscriber | `ons.interaction.caller_type` — new, returning, subscriber | MATCH |
| customer_type | home, business | `ons.interaction.customer_type` — home, business | MATCH |
| session_path | NO_SESSION, SESSION_NOW, CALLBACK, ONSITE_QUEUE, NOT_APPLICABLE, SESSION_SCHEDULED | `ons.interaction.session_path` — no_session, session_now, callback, onsite_queue, not_applicable, session_scheduled | MATCH (lowercased) |
| pipeline_stages (12 canonical) | intake_submitted → ... → closed_won/closed_lost | `ons.case.stage` + `ons.session.pipeline_stage` (NOT BUILT) | PLANNED |

---

## Summary Scorecard

| Domain | Legacy Tables | Odoo Models | Status | Blockers |
|--------|--------------|-------------|--------|----------|
| **Intake** | submissions, call_logs | ons.interaction | **BUILT** | Phone matching uses `ilike` (see doc 22) |
| **Customer** | customer_profiles | res.partner (extended) | **BUILT** | Missing alternate_phone mapping |
| **Drivers** | call_driver_codes, call_driver_categories | ons.call.driver | **BUILT** | Category is Selection not M2O (acceptable) |
| **CRM** | (none — underdeveloped in legacy) | crm.lead (extended) | **BUILT** | Minimal — only interaction_id link |
| **Cases** | cases, jobs, service_sessions | ons.case, ons.session | **PLANNED** | Prompt 4 scope |
| **Billing** | payment_transactions | account.move, account.payment | **PLANNED** | Prompt 4 scope |
| **Callbacks** | callbacks | ons.callback (proposed) | **NOT STARTED** | Needs dedicated model (doc 21 recommendation) |
| **Dispatch** | workmarket_assignments | ons.dispatch | **PLANNED** | Prompt 5+ scope |
| **QA** | qa_evaluations | ons.qa.evaluation | **PLANNED** | Prompt 5+ scope |
| **3CX Realtime** | realtime_call_sessions, agent_status_slices | ons.threecx.* | **NOT STARTED** | Daemon + module scope |
| **Email** | inbox_messages | mail.message (stock) | **STOCK** | Shared inbox UI gap |
| **Security** | app_users, roles | res.users + ons_ops_core groups | **BUILT** | 3-tier: Agent→Manager→Admin |

---

## Contract Freeze Commitments

The following contracts are **FROZEN** effective this document:

1. **ons.interaction** — field names, types, and constraints as implemented. No breaking changes without migration script.
2. **ons.call.driver** — code field is the stable identifier. 30 seed codes are permanent (may add, never rename).
3. **res.partner extensions** — `customer_segment`, `subscription_status`, `lifetime_value` field names frozen.
4. **crm.lead extension** — `interaction_id` field frozen.
5. **Security groups** — `ons_ops.group_agent`, `ons_ops.group_manager`, `ons_ops.group_admin` frozen.
6. **Sequence format** — `INT-YYYYMMDD-XXXX` frozen for interaction references.

Future modules (`ons_ops_cases`, `ons_ops_billing`, etc.) MUST NOT:
- Rename any frozen field
- Remove any frozen field
- Change the type of any frozen field
- Alter the security group hierarchy
- Modify the interaction state machine without adding states (never removing)
