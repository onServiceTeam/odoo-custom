# 40 — Cases and Sessions Contract

**Date:** 2026-04-02  
**Purpose:** Define the exact rules for cases, sessions, stages, the session tracker, and the lead→case boundary before building `ons_ops_cases`.

---

## 1. What Is a Case

A **case** (`ons.case`) is a service engagement with a confirmed customer. It represents active work toward resolution — remote session, troubleshooting, onsite dispatch, or verification/billing.

**Legacy equivalent:** One `submissions` row with `online_session_started=true` OR progression past triage.

**Key principle:** Not every interaction becomes a lead. Not every lead becomes a case. A case means the business has committed resources to serve this customer.

---

## 2. What Is a Session

In the legacy system, "session" is NOT a separate database entity — it is a **computed pipeline stage** of the submission. The "session tracker" is a filtered, staged **view** of submissions.

**Decision: Session is NOT a separate model.**

A session is a case in stages 4–8 (Online Session Started through Billing In Progress). The `ons.case` model tracks this with stage progression. No separate `ons.session` model is needed because:
- Legacy has one `submissions` table, not two
- The "session" concept is just "case with active work happening"
- A separate model would create sync/ownership confusion

---

## 3. Case Creation Rules

A case is created when:

| Source | Trigger | Partner Required? |
|--------|---------|:-----------------:|
| Lead → Case | Lead is convertible (`is_convertible=True`) + agent action | YES |
| Interaction → Case (direct) | session_path ∈ (session_now, onsite_queue) + partner resolved | YES |
| Manual creation | Agent creates manually for walk-in/special | YES |

A case is NOT created for:
- Inquiry-only interactions (billing, admin)
- Declined/lost leads
- Voicemail / missed / abandoned calls
- Unresolved identity (no partner)

---

## 4. Required Case Stages (12 Canonical)

Mapping legacy `pipeline_stage_canonical` to Odoo case stages:

| # | Code | Label | Legacy Equivalent | Is Closed? | Is Won? |
|---|------|-------|-------------------|:----------:|:-------:|
| 1 | `intake_submitted` | Intake Submitted | intake_submitted | NO | NO |
| 2 | `triage_in_progress` | Triage In Progress | triage_in_progress | NO | NO |
| 3 | `callback_scheduled` | Callback Scheduled | callback_scheduled | NO | NO |
| 4 | `session_started` | Session Started | online_session_started | NO | NO |
| 5 | `handoff_to_tech` | Handoff to Tech | handoff_to_assisting | NO | NO |
| 6 | `repair_in_progress` | Repair In Progress | repair_in_progress | NO | NO |
| 7 | `ready_for_verification` | Ready for Verification | ready_for_verification | NO | NO |
| 8 | `billing_in_progress` | Billing In Progress | billing_in_progress | NO | NO |
| 9 | `paid` | Paid | paid | NO | NO |
| 10 | `closed_won` | Closed Won | closed_won | YES | YES |
| 11 | `closed_lost` | Closed Lost | closed_lost | YES | NO |
| 12 | `onsite_dispatched` | Onsite Dispatched | onsite_dispatched | NO | NO |

**Note:** Stages 1–9 and 12 are active. Stages 10–11 are terminal.

---

## 5. Case Invariants

1. A case MUST have a `partner_id` (resolved customer)
2. A case MUST have at least one interaction linked
3. A case has exactly ONE current stage at any time
4. Stage changes are logged in `ons.case.stage.history` with timestamps
5. Terminal stages (closed_won, closed_lost) can be reopened by managers
6. `online_session_started` flag matches legacy behavior: set when stage ≥ session_started
7. Time-in-stage is computed from the stage history entries

---

## 6. Case Ownership and Assignment

| Role | Field | Required? | When Set |
|------|-------|:---------:|----------|
| Intake Agent | `intake_agent_id` | YES | At case creation (from interaction.agent_id) |
| Assigned Technician | `assigned_tech_id` | NO | When work begins (stage ≥ session_started) |
| Billing Agent (VBT) | `billing_agent_id` | NO | When stage reaches billing_in_progress |

**Legacy mapping:**
- `submitted_by` → `intake_agent_id`
- `assisting_tech_id` → `assigned_tech_id`
- `billing_tech_id` → `billing_agent_id`

---

## 7. Case Links

| Target | Field | Purpose |
|--------|-------|---------|
| `ons.interaction` | `interaction_ids` (One2many) | All interactions for this case |
| `ons.interaction` | `source_interaction_id` (Many2one) | Original intake interaction |
| `crm.lead` | `lead_id` (Many2one) | Source lead if converted from pipeline |
| `res.partner` | `partner_id` (Many2one) | Customer (REQUIRED) |
| `ons.call.driver` | `primary_driver_id` (Many2one) | Issue category |
| Future: `ons.dispatch` | `dispatch_ids` | Onsite jobs (Prompt 8) |
| Future: billing | `invoice_ids` | Invoices (Prompt 6) |

---

## 8. Aging and Overdue

| Field | Computation | Legacy Equivalent |
|-------|-------------|-------------------|
| `hours_in_pipeline` | `(now - create_date) / 3600` | `hours_in_pipeline` |
| `days_old` | `(now - create_date).days` | `days_old` |
| `aging_bucket` | 0–4h / 4–24h / 24–48h / 48–72h / 72h+ | `aging_bucket` |
| `is_overdue` | payment_status = 'for_collection' | `is_overdue` (mapped to billing Prompt 6) |

Aging tracks from `create_date` (when case first created), not stage entry.

---

## 9. Session Tracker Display Columns

The session tracker is NOT a separate view — it is the primary case list with specific filters and columns:

| Column | Source Field | Notes |
|--------|------------|-------|
| Reference | `name` | Case sequence CASE-XXXX |
| Customer | `partner_id` | |
| Phone | `partner_phone` | Related from partner |
| Intake Agent | `intake_agent_id` | |
| Technician | `assigned_tech_id` | |
| Billing Agent | `billing_agent_id` | |
| Driver | `primary_driver_id` | Issue category |
| Stage | `stage_id` | Colored badge |
| Time in Pipeline | `hours_in_pipeline` | Computed |
| Aging | `aging_bucket` | Computed |
| Next Action | `next_action` | Free text |
| Next Action At | `next_action_at` | Datetime |

**Default Filters (exclude from tracker):**
- `is_closed = False` (exclude won/lost)
- Active cases only

---

## 10. Lead → Case Conversion Boundary

### Prerequisites
1. Lead `is_convertible = True` (partner set, service path, not declined)
2. Lead stage ≥ Qualified (stock CRM stage_id=2)

### What Happens
1. `ons.case` created with:
   - `partner_id` from lead
   - `lead_id` = source lead
   - `source_interaction_id` = lead's interaction_id
   - `intake_agent_id` = lead's user_id
   - `primary_driver_id` = lead's primary_driver_id
   - Initial stage = `intake_submitted`
2. Lead stage → Won (stock stage_id=4, is_won=True)
3. Lead gets `case_id` reverse link for navigation

### Edge Cases
- **No partner:** Blocked — conversion requires partner_id
- **Only phone + first name:** Partner must be created/resolved first
- **Previously declined, now returning:** New lead → new case (old lead stays lost)
- **Repeated caller, existing case open:** Link interaction to existing case, not new case

---

## 11. Future Integration Points

| System | How Cases Connect | Built In |
|--------|------------------|----------|
| Billing/Invoicing | case → invoice via product lines | Prompt 6 |
| 3CX Telephony | call → interaction → case | Prompt 7 |
| Dispatch | case → dispatch record | Prompt 8 |
| Communications | case → chatter + Discuss | Prompt 9 |
| AI summaries | case → AI outputs | Prompt 10 |
| QA reviews | case → QA results | Prompt 11 |
| Reporting | case stages → funnel metrics | Prompt 12 |

---

## 12. Stage Override Capability

Legacy has `session_tracker_overrides.pipeline_stage_override` for manual stage forcing.

**Odoo equivalent:** Managers can manually set any stage on a case form. The `action_force_stage()` method logs the override in chatter and stage history with `override=True` flag. This is NOT the normal flow — it's an escape hatch for edge cases.
