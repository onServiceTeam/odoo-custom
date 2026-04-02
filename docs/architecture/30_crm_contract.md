# 30 — CRM Contract

**Date:** 2026-04-02  
**Purpose:** Define the exact rules for leads, inquiries, callbacks, consent, and the interaction→lead boundary before building `ons_ops_crm`.

---

## What Becomes a Lead

An `ons.interaction` becomes a `crm.lead` when ALL of these are true:

1. **Interaction is classified** (`state` ≥ `classified`, `primary_driver_id` set)
2. **Session path indicates potential sale** — the caller needs something the business sells
3. **At least ONE of:**
   - `session_path` = `session_now` | `callback` | `session_scheduled` (service lead)
   - `session_path` = `no_session` AND driver indicates sales intent (e.g., `BILLING_QUESTION`, renewal inquiry, upsell opportunity)
4. **NOT purely administrative** — billing status checks, wrong numbers, spam, etc. stay as interaction-only

### Legacy Decision Logic (from `callContextPhase3.ts`)

| Legacy `callPurpose` | Legacy `lifecycleStage` | Odoo Action |
|----------------------|------------------------|-------------|
| `diagnose_and_convert` | `lead_intake` | Create lead (type=`lead` or `opportunity` based on readiness) |
| `tech_callback_voicemail` | varies | Create lead with `callback_requested=True` |
| `verification_only` / `verification_plus_billing` | `verification_and_billing` | No new lead — this is case/session territory (Prompt 5) |
| `billing_or_admin_only` | `non_job_contact` | **No lead** — interaction-only, mark completed |

---

## What Stays Just an Interaction

These interaction types never generate a lead:

1. **Missed calls** (`disposition=missed`) — no classification data
2. **Abandoned calls** (`disposition=abandoned`) — caller hung up
3. **Voicemail** — creates interaction for logging, but no lead unless agent reviews and promotes
4. **Administrative inquiries** — billing questions, password resets, account checks
5. **Spam / wrong number** (`session_path=not_applicable`)
6. **Internal calls** (`direction=internal`)

---

## When a Partner Is Required

| Action | Partner Required? | Rule |
|--------|------------------|------|
| Create interaction | NO | Raw data comes from 3CX; may not match any partner |
| Create lead from interaction | NO (strongly recommended) | Lead can exist with phone+name only; partner resolution encouraged |
| Convert lead to case (Prompt 5) | YES | Case MUST have a resolved partner for service delivery |
| Record consent | YES | Consent is per-partner, not per-interaction |

---

## When a Lead Is Convertible to a Case

A lead moves from CRM pipeline to case pipeline when:

1. `partner_id` is set (customer identified)
2. `session_path` ∈ (`session_now`, `callback`, `onsite_queue`, `session_scheduled`)
3. Lead is NOT marked `declined` or `lost`
4. Lead is in appropriate stage (≥ Qualified)

This boundary is documented but NOT enforced in Prompt 4. The actual `action_convert_to_case` will be built in Prompt 5 (`ons_ops_cases`).

---

## Required Lead Stages

Stock Odoo CRM provides: New → Qualified → Proposition → Won.

These are sufficient. We do NOT add custom stages because:
- Stock stages are upgrade-safe
- The business's real "stages" happen inside cases/sessions (Prompt 5), not CRM
- Adding stages here would duplicate the session tracker concept

**Custom lost reasons (replacing stock defaults):**

| Lost Reason | Legacy Equivalent | When Used |
|-------------|-------------------|-----------|
| Customer Declined Service | `repair_status='cancelled'` | Customer said no during intake |
| Too Expensive | stock | Price objection |
| Went to Competitor | new | Customer chose another provider |
| Issue Self-Resolved | new | Problem fixed before session |
| No Response / Unreachable | `callback_status='no_answer'` | Multiple attempts failed |
| Not Serviceable | new | Technical limitation prevents service |
| Duplicate Lead | new | Identified as duplicate after creation |

---

## Required Consent Objects and Invariants

### Why Custom Consent Model

Legacy has `consentVerified: boolean` on voice calls, plus dispatch cancellation reasons tracking. The business needs explicit, auditable, channel-specific consent tracking for:
- Email marketing
- SMS notifications  
- Callback permission
- Service terms acceptance

Stock Odoo has `mail.blacklist` (global email opt-out) but no per-channel, per-scope consent tracking.

### Model: `ons.contact.consent`

| Field | Type | Notes |
|-------|------|-------|
| partner_id | Many2one → res.partner | REQUIRED — consent is per-customer |
| channel | Selection | email / sms / phone / any |
| scope | Selection | marketing / operational / callback / renewal / service_terms |
| status | Selection | pending / opted_in / double_opted_in / opted_out / revoked |
| capture_source | Selection | web_form / phone_call / email_reply / sms_reply / manual |
| captured_by_id | Many2one → res.users | Agent who recorded consent |
| interaction_id | Many2one → ons.interaction | If consent captured during call |
| opted_in_at | Datetime | When single opt-in recorded |
| confirmed_at | Datetime | When double opt-in confirmed (null = single only) |
| opted_out_at | Datetime | When customer withdrew consent |
| revoked_at | Datetime | When admin revoked (compliance) |
| evidence | Text | Notes/proof of consent |
| active | Boolean | Archivable |

### Consent Invariants

1. A partner may have at most ONE active consent record per (channel, scope) pair
2. `opted_out` and `revoked` are terminal states — a new consent record must be created to re-opt-in
3. `double_opted_in` requires `confirmed_at` to be set
4. `pending` means consent was requested but not yet confirmed
5. Consent records are NEVER deleted — only archived or status-changed (audit trail)

---

## Lead Type / Inquiry Classification

### Custom Fields on `crm.lead` (via `ons_ops_crm`)

| Field | Type | Purpose |
|-------|------|---------|
| `interaction_id` | Many2one | Already exists (from ons_ops_intake) — source interaction |
| `lead_type` | Selection | inquiry / callback_request / service_lead / nurture / renewal |
| `caller_relationship` | Selection | first_time_lead / returning_no_plan / active_subscriber / past_subscriber |
| `callback_requested` | Boolean | Customer wants callback |
| `callback_preferred_time` | Char | Free-text preferred time |
| `declined_reason` | Text | Why customer declined (free text) |
| `is_nurture_eligible` | Boolean | Computed: lead not lost, has contact info, consented to marketing |
| `is_convertible` | Boolean | Computed: partner set, session_path is service, not declined |
| `decline_date` | Date | When marked declined |
| `primary_driver_id` | Many2one → ons.call.driver | Copied from interaction for quick filtering |
| `customer_phone_raw` | Char | Related from interaction for search |

### Lead Type Definitions

| lead_type | Meaning | Creates From |
|-----------|---------|-------------|
| `inquiry` | Information request only, no service intent | Admin/billing interactions |
| `callback_request` | Customer wants callback, not yet triaged | Callback interactions |
| `service_lead` | Active service opportunity | session_path = session_now/scheduled |
| `nurture` | Not ready now, may convert later | Declined but consented |
| `renewal` | Existing customer renewal/upsell | Returning/subscriber callers |

---

## Interaction → Lead Matrix

| session_path | driver category | caller_type | Result |
|-------------|----------------|-------------|--------|
| session_now | any technical | any | service_lead |
| callback | any | any | callback_request |
| session_scheduled | any technical | any | service_lead |
| onsite_queue | any | any | service_lead |
| no_session | billing | any | inquiry (no lead unless agent promotes) |
| no_session | technical (upsell=true) | returning/subscriber | renewal |
| no_session | technical (upsell=false) | new | inquiry or nurture |
| not_applicable | any | any | NO LEAD (interaction-only) |

---

## Repeated Callers

| Scenario | Rule |
|----------|------|
| Same phone, new call, lead exists in pipeline | Attach interaction to existing lead (don't create duplicate) |
| Same phone, new call, lead is won/lost | Create NEW lead (new opportunity) |
| Same phone, different issue | Create NEW lead (different driver code = different need) |
| Same phone, no existing lead | Create new lead |
| Ambiguous phone match (multiple partners) | Do NOT auto-attach. Agent resolves manually. |
