# 23 — Legacy Parity Gaps

**Date:** 2026-05-31  
**Purpose:** Classify every legacy middleware domain as preserved, partially preserved, not yet preserved, or wrongly modeled in Odoo.  
**Method:** Every finding proved from middleware schema (213+ migrations) vs. current Odoo module code.

---

## Classification Legend

| Status | Meaning |
|--------|---------|
| **PRESERVED** | Semantic equivalent exists in Odoo with matching data, constraints, and behavior |
| **PARTIAL** | Core fields/logic exist but secondary features are missing or simplified |
| **NOT YET** | Domain is planned (appears in architecture docs) but no Odoo code exists |
| **WRONG** | Odoo implementation conflicts with legacy semantics — must fix before Prompt 4 |

---

## Domain-by-Domain Analysis

### 1. Intake / Submissions — PARTIAL

**What's preserved:**
- Customer contact capture (name, phone, email) ✓
- Interaction type + direction ✓
- Agent attribution (agent_id, assisting_agent_id, billing_agent_id) ✓
- Call driver classification (primary + secondary) ✓
- Session path routing decision ✓
- Caller type (new/returning/subscriber) ✓
- Customer type (home/business) ✓
- 3CX CDR dedup key (threecx_cdr_id with unique constraint) ✓
- Call timing (start, end, duration, talk_duration) ✓
- Recording link (has_recording, recording_url) ✓
- Transcript + status ✓
- State machine (new → classified → assigned → completed) ✓

**What's missing:**
| Legacy Field | Status | Impact | Resolution |
|-------------|--------|--------|------------|
| `amount`, `service_purchased`, `base_product_type` | NOT YET | Financial data. Will go on `ons.session` (Prompt 4) | Low — not needed for intake |
| `is_subscription` | NOT YET | Subscription flag. Will use `partner.subscription_status` + session data | Low |
| `next_action`, `next_action_at` | NOT YET | Follow-up scheduling. Maps to `mail.activity` | Low — stock Odoo feature |
| `reopened_at`, `reopened_by` | NOT YET | Case reopening. Will be tracked on `ons.case` changelog | Low |
| `customer_segment` on interaction | By design | Segment is per-partner not per-interaction in Odoo | Correct design |
| `ring_duration`, `hold_duration`, `wait_duration` | Omitted | Detailed call metrics. Rarely used in business logic | Low — add as JSONB/metadata if needed |
| `discord_channel_id`, `discord_message_url` | Legacy | Discord being deprecated per doc 15 | N/A |
| `odoo_invoice_id`, `odoo_invoice_number` | NOT YET | Invoice linking. Will be on `ons.session` → `account.move` | Prompt 4 |

**Verdict: PARTIAL** — Core intake semantics fully preserved. Financial and follow-up fields correctly deferred to case/session models.

---

### 2. Call Logs / Telephony — PARTIAL

**What's preserved:**
- Call data merged into `ons.interaction` (call_start, call_end, duration, disposition) ✓
- 3CX CDR dedup via `threecx_cdr_id` ✓
- Recording URL and has_recording flag ✓
- Direction (inbound/outbound/internal) ✓
- Agent linkage ✓
- Transcript ✓

**What's missing:**
| Legacy Field | Status | Impact | Resolution |
|-------------|--------|--------|------------|
| `phone_number_normalized` (stored, indexed) | Omitted | Phone matching does normalization on-the-fly | OK for < 100K partners. Add stored field if perf issue (doc 22) |
| `agent_extension` | NOT YET | 3CX extension mapping. Belongs in `ons_ops_3cx` | Future module |
| `threecx_call_id` (realtime tracking) | NOT YET | Active call tracking. Belongs in `ons_ops_3cx` | Future module |
| `contact_id` (direct customer_profiles FK) | N/A | Odoo uses `partner_id` (same semantic) | ✓ |
| `customer_status_at_call` (new/known/has_history) | Omitted | Can be computed from partner history at query time | Low priority |
| `service_session_id`, `case_id` | NOT YET | Session/case linking. Planned for Prompt 4 | Expected |

**Verdict: PARTIAL** — Core telephony data preserved. 3CX-specific real-time features deferred to dedicated module.

---

### 3. Customer Profiles — PRESERVED

**What's preserved:**
- Contact info (name, phone, email, address) → res.partner stock fields ✓
- Customer segment (new/returning/subscriber/vip) → `customer_segment` Selection ✓
- Subscription status (none/active/cancelled/expired) → `subscription_status` Selection ✓
- Lifetime value → `lifetime_value` Float ✓
- Interaction count → `interaction_count` computed field ✓
- Odoo partner ID mapping → native (Odoo IS the master) ✓

**What's missing:**
| Legacy Field | Status | Impact | Resolution |
|-------------|--------|--------|------------|
| `total_orders`, `total_cases`, `total_sessions`, `total_spent` | NOT YET | Denormalized counters. Will be computed from `ons.case` + `account.move` | Prompt 4+ |
| `first_contact_date`, `last_contact_date` | Computable | Can be derived from `ons.interaction` min/max dates | Low — add computed field if needed |
| `tags` TEXT[] | Partial | Odoo has `res.partner.category_id` (M2M, equivalent) | Stock feature |
| `phone_clean` (stored normalized) | N/A | Odoo uses `phone_sanitized` (E.164, equivalent) | ✓ |
| `alternate_phone` | Stock | Maps to `res.partner.mobile` | ✓ |

**Verdict: PRESERVED** — All critical customer fields covered by stock Odoo + custom extensions.

---

### 4. Call Driver Taxonomy — PRESERVED

**What's preserved:**
- Code (unique identifier) ✓
- Category (20 selections covering all legacy categories) ✓
- Detection keywords + common phrases ✓
- Handling instructions ✓
- Business flags (requires_callback, requires_onsite, is_upsell_opportunity) ✓
- Coaching priority ✓
- 30 seed records covering all legacy driver codes ✓

**What's simplified:**
| Legacy Aspect | Odoo Change | Rationale |
|--------------|-------------|-----------|
| `category_id` FK → separate table | `category` Selection field | Categories are static in practice; Selection simpler than maintaining a second model |
| `qa_rubric_id` FK | Not modeled | QA rubric belongs in `ons_ops_ai` module |
| `usage_count` denormalized | `interaction_count` computed live | Better: always accurate, no staleness |
| `example_descriptions` separate field | Folded into `description` | Fewer fields, same information |

**Verdict: PRESERVED** — Full semantic parity with acceptable simplifications.

---

### 5. Payment / Revenue — NOT YET

**Legacy:** `payment_transactions` table is THE source of truth for revenue. 30+ fields covering multi-source payments (Stripe, Zoho, Odoo, manual), agent attribution, conflict resolution, sync tracking.

**Odoo:** No custom billing module exists. Stock `account.move` and `account.payment` are available but not extended.

**Planned:** `ons_ops_billing` module (doc 12, Tier 5) will:
- Bridge `account.move` to Stripe/Zoho webhooks
- Track agent billing attribution
- Handle conflict resolution for duplicate payments
- Maintain revenue source audit trail

**Gaps requiring design decisions:**
1. **Multi-source sync tracking** (found_in_stripe, found_in_zoho_books, etc.) — needs custom fields on `account.move` or a pivot table
2. **Conflict resolution** (has_conflict, confidence_score) — no stock Odoo equivalent
3. **Conversion attribution** (intake/fixing/billing credit split) — needs custom `ons.conversion.attribution` model or extension

**Verdict: NOT YET** — No code exists. Properly deferred to Prompt 4.

---

### 6. Callbacks — NOT YET

**Legacy:** Dedicated `callbacks` table with scheduling, priority, auto-escalation (overdue → urgent), auto-archive (7 days → archived), assignment, and completion tracking.

**Odoo:** No custom callback model exists. Stock `mail.activity` has date_deadline but lacks priority, escalation, and archive semantics.

**Analysis:**
| Feature | mail.activity (stock) | Custom ons.callback | Decision |
|---------|----------------------|---------------------|----------|
| Scheduling | date_deadline only | Full datetime + timezone | Custom needed |
| Priority | No | low/normal/high/urgent | Custom needed |
| Auto-escalate | No | Cron to escalate overdue | Custom needed |
| Auto-archive | No | 7-day attention timer | Custom needed |
| Assignment | user_id | assigned_to + team-visible | Custom needed |

**Verdict: NOT YET** — Stock activity insufficient. Recommended: dedicated `ons.callback` model within `ons_ops_cases`.

---

### 7. Cases / Service Sessions — NOT YET

**Legacy:** `cases` table + `service_sessions` table + `jobs` table. Cases track customer problems. Sessions track individual work sessions within a case. Jobs track assisting technician work.

**Odoo:** Planned as `ons.case` + `ons.session` (doc 11). No code exists.

**Key semantic to preserve:**
- A case groups sessions (1:many)
- A session has a pipeline stage (the 12 canonical stages)
- The pipeline is a COMPUTED virtual view in legacy, not a single column
- Agent handoff between intake → fixing → billing tracked across session stages
- SLA tracking with breach detection

**Verdict: NOT YET** — Prompt 4 scope. Architecture doc 11 provides the specification.

---

### 8. Dispatch / WorkMarket — NOT YET

**Legacy:** `workmarket_assignments` table. External dispatch to field technicians via WorkMarket API.

**Odoo:** Planned as `ons.dispatch` (doc 11). No code exists.

**Verdict: NOT YET** — Future module (`ons_ops_dispatch`).

---

### 9. QA / Quality Evaluation — NOT YET

**Legacy:** `qa_evaluations` table + `qa_rubrics` table. AI-assisted grading + human review.

**Odoo:** Planned as `ons.qa.evaluation` + `ons.qa.rule` (doc 11). No code exists.

**Verdict: NOT YET** — Future module (`ons_ops_ai`).

---

### 10. Realtime 3CX / Agent Status — NOT YET

**Legacy:** `realtime_call_sessions` + `realtime_agent_status_slices`. Sub-30-second polling of 3CX PBX.

**Odoo:** Planned as `ons.threecx.queue` + `ons.threecx.agent` (doc 12). No code exists. Will be pushed by external daemon (doc 15).

**Verdict: NOT YET** — Daemon + `ons_ops_3cx` module.

---

### 11. Email / Inbox — STOCK

**Legacy:** `inbox_messages` table with shared inbox, folders, read/unread, spam filtering.

**Odoo:** Stock `mail.message` + `mail.mail` + `fetchmail.server` + `mail.alias`. Handles email natively.

**Gap:** Shared inbox UI (folder view, team visibility) not available OOTB. May need `ons_ops_comms` for team inbox view.

**Verdict: STOCK** — Core email handled by Odoo. UI gap for shared inbox.

---

### 12. Security / Users — PRESERVED

**Legacy:** `app_users` table with role-based access.

**Odoo:** `ons_ops_core` provides 3-tier group hierarchy:
- `ons_ops.group_agent` (base level)
- `ons_ops.group_manager` (implies agent)
- `ons_ops.group_admin` (implies manager)

All with proper `implies` chains. 9 tests covering group existence, hierarchy, and transitive permissions.

**Verdict: PRESERVED** — Full parity with stock Odoo group mechanism.

---

## ~~WRONG~~ Items (Issues Found and Fixed)

### FIXED: Phone Matching Algorithm

**Problem:** `action_resolve_customer()` used `ilike` (substring match) instead of legacy's exact last-10-digit comparison.

**Impact:** Could match wrong partner if phone substring overlaps. `limit=1` picks arbitrarily.

**Fix applied:** Deterministic last-10-digit exact match. Multiple matches refuse to auto-link. See doc 22.

**Status:** FIXED in this audit. Tests added.

### No Other WRONG Items Found

All other Odoo models correctly represent their legacy counterparts:
- ✓ Field types match (no Char where Integer needed, etc.)
- ✓ Required fields match
- ✓ Unique constraints match
- ✓ State machines are subsets of legacy (can be extended, not conflicting)
- ✓ Enum values match (after normalization: lowercase, underscores)

---

## Summary Scorecard

| Domain | Tables in Legacy | Status | Prompt |
|--------|-----------------|--------|--------|
| Intake / Submissions | submissions, call_logs | **PARTIAL** | 3 (done) |
| Customer Master | customer_profiles | **PRESERVED** | 3 (done) |
| Call Drivers | call_driver_codes, call_driver_categories | **PRESERVED** | 3 (done) |
| CRM | (new functionality) | **PRESERVED** | 3 (done) |
| Security | app_users, roles | **PRESERVED** | 2 (done) |
| Payments / Revenue | payment_transactions | **NOT YET** | 4 |
| Cases / Sessions | cases, service_sessions, jobs | **NOT YET** | 4 |
| Callbacks | callbacks | **NOT YET** | 4 |
| Dispatch | workmarket_assignments | **NOT YET** | 5+ |
| QA | qa_evaluations, qa_rubrics | **NOT YET** | 5+ |
| 3CX Realtime | realtime_call_sessions, agent_status | **NOT YET** | 5+ |
| Email | inbox_messages | **STOCK** | N/A |

**Total legacy tables:** 15+  
**Fully preserved:** 4 domains (Customer, Drivers, CRM, Security)  
**Partially preserved:** 2 domains (Intake, Telephony)  
**Not yet started:** 6 domains (properly deferred)  
**Wrongly modeled:** 0 (after phone matching fix)
