# 21 — Interaction / Lead / Case Boundary Contract

**Date:** 2026-05-31  
**Purpose:** Define the exact boundary between `ons.interaction`, `crm.lead`, and the planned `ons.case` / `ons.session` models. Answer the 6 critical workflow questions.

---

## Entity Relationship (Current + Planned)

```
                     ┌────────────────┐
                     │  res.partner   │  ← Customer master (Odoo stock)
                     └───────┬────────┘
                             │ partner_id
                             │
                    ┌────────▼────────┐
                    │ ons.interaction  │  ← BUILT (Prompt 3)
                    │ Atomic contact   │     Every inbound event: call, email, SMS, web
                    │ event            │     Lifecycle: new → classified → assigned → completed
                    └──┬──────────┬───┘
                       │          │
            CRM path   │          │  Service path
                       │          │
              ┌────────▼───┐  ┌───▼──────────┐
              │  crm.lead  │  │  ons.case    │  ← PLANNED (Prompt 4)
              │  (stock)   │  │  Support case │
              │            │  │  1:many sessions
              │  Sells /   │  │  Tracks resolution
              │  nurtures  │  └───┬──────────┘
              └────────────┘      │
                                  │ case_id
                            ┌─────▼──────────┐
                            │  ons.session   │  ← PLANNED (Prompt 4)
                            │  Work session  │
                            │  Pipeline stages│
                            │  Payment link  │
                            └────────────────┘
```

---

## Boundary Definitions

### ons.interaction — WHAT HAPPENED

**Role:** The atomic, immutable record of a customer contact event.

| Property | Value |
|----------|-------|
| **Creates when** | A call arrives (3CX daemon), email received, SMS received, web form submitted |
| **Never creates** | Internal notes, follow-up activities, system events |
| **Owns** | Raw contact data: phone number, caller name, call duration, disposition, recording, transcript |
| **Does NOT own** | Case lifecycle, billing, payment, SLA, dispatch |
| **Links to** | `partner_id` (resolved customer), `lead_id` (if CRM path), future `case_id` (if service path) |
| **State machine** | `new` → `classified` → `assigned` → `completed` |
| **Completed means** | Classification done AND linked to exactly one of {lead, case, or interaction-only} |
| **Mutability** | After creation: classification fields may be updated. Raw call data is immutable. |
| **Approximate mapping** | Legacy `submissions` (intake data) + `call_logs` (telephony data) merged |

**Frozen fields (from doc 20):** name, interaction_type, direction, state, partner_id, customer_phone, agent_id, primary_driver_id, threecx_cdr_id, session_path, call_start, call_end, call_duration, disposition.

### crm.lead — WHERE WE SELL

**Role:** Odoo stock CRM lead/opportunity for sales pipeline tracking.

| Property | Value |
|----------|-------|
| **Creates when** | Interaction classified as sales opportunity (not service) |
| **Creates from** | `ons.interaction` where session_path = no_session AND customer shows buying intent |
| **Owns** | Expected revenue, probability, sales stage, nurture activities |
| **Does NOT own** | Call recording, transcript, disposition — those stay on interaction |
| **Links to** | `interaction_id` Many2one → ons.interaction (custom field, BUILT) |
| **State machine** | Stock Odoo: New → Qualified → Proposition → Won/Lost |
| **Approximate mapping** | Legacy had NO formal CRM pipeline — this is NEW functionality |

**Extension on crm.lead:** Only `interaction_id` field added. No other customization.

### ons.case — HOW WE FIX IT (PLANNED)

**Role:** Groups related sessions for one customer problem. Tracks SLA, escalation, resolution.

| Property | Value |
|----------|-------|
| **Creates when** | Interaction classified as service request (session_path ≠ no_session) |
| **Creates from** | `ons.interaction` via `action_assign()` or automation |
| **Owns** | Subject, priority, SLA, assigned agent, escalation, resolution notes, kanban stage |
| **Does NOT own** | Call recording (interaction), payment amount (session), dispatch details (dispatch) |
| **Links to** | `primary_interaction_id`, `partner_id`, `session_ids` (One2many), `dispatch_ids` (One2many) |
| **State machine** | Kanban stages: Open → In Progress → Pending Customer → Resolved → Closed |
| **Approximate mapping** | Legacy `cases` table |

### ons.session — HOW WE WORK ON IT (PLANNED)

**Role:** Individual work session within a case. One case may have multiple sessions.

| Property | Value |
|----------|-------|
| **Creates when** | Technician starts working with customer (remote session, callback, onsite) |
| **Creates from** | Case assignment action |
| **Owns** | Session type, pipeline stage, duration, outcome, product sold, payment collected |
| **Does NOT own** | SLA (case), call recording (interaction), dispatch logistics (dispatch) |
| **Links to** | `case_id`, `partner_id` (related), `interaction_id` (originating call), `call_ids` (calls during session) |
| **State machine (pipeline)** | new → troubleshooting → in_session → awaiting_billing → paid → completed |
| **Approximate mapping** | Legacy `service_sessions` + `jobs` merged |

---

## The 6 Critical Workflow Questions

### Q1: When does an interaction become a case vs. a lead?

**Answer — Decision Tree:**

```
Interaction created (state=new)
  │
  ├─ AI classifies driver (state=classified)
  │   │
  │   ├─ session_path = no_session AND driver indicates sales/renewal
  │   │   └─ → CREATE crm.lead, link interaction.lead_id
  │   │
  │   ├─ session_path IN (session_now, callback, onsite_queue, session_scheduled)
  │   │   └─ → CREATE ons.case, link interaction.case_id
  │   │
  │   ├─ session_path = no_session AND driver is informational (e.g., BILLING_QUESTION)
  │   │   └─ → COMPLETE interaction directly (no case, no lead)
  │   │
  │   └─ session_path = not_applicable (spam, wrong number)
  │       └─ → COMPLETE interaction directly
  │
  └─ Not classified (state=new, no driver)
      └─ Remains in queue for manual review
```

**Rule:** An interaction links to AT MOST ONE of {crm.lead, ons.case}. Never both. The `session_path` field is the primary discriminator.

### Q2: Can one interaction create multiple cases?

**Answer: NO.**  
One interaction → one case (or one lead, or neither). This is enforced by the Many2one relationship from interaction to case.

However: One CUSTOMER (res.partner) can have many cases. And one case can accumulate MULTIPLE interactions (e.g., a callback creates a second interaction linked to the same case).

### Q3: What triggers case closure vs. lead closure?

| Entity | Closed When | Mechanism |
|--------|-------------|-----------|
| **Interaction** | `state=completed` — classification done and routed | `action_complete()` method |
| **crm.lead** | Won (converted) or Lost (marked lost) | Stock Odoo `action_set_won()` / `action_set_lost()` |
| **ons.case** | All sessions resolved AND payment collected (or waived) | Kanban stage to "Closed" (is_closing=True on stage) |
| **ons.session** | Work done + billing complete OR no_sale outcome | Pipeline stage to "completed" |

**Critical invariant:** A case CANNOT close while any session is in an active pipeline stage. Enforcement will be in `ons_ops_cases` module.

### Q4: Who owns agent attribution?

```
INTAKE CREDIT:     interaction.agent_id          (phone_tech_id in legacy)
FIXING CREDIT:     interaction.assisting_agent_id (assisting_tech_id in legacy)
                   — OR session.primary_agent_id / session.assisting_agent_id
BILLING CREDIT:    interaction.billing_agent_id   (billing_tech_id in legacy)
                   — OR session.billing_agent (TBD)
CONVERSION CREDIT: Derived from all three above (used in revenue reports)
```

**Current state:** All three agent fields exist on `ons.interaction` (BUILT). When `ons.session` is added, the session will ALSO carry agent assignments (for mid-case handoffs). Revenue attribution will look at the session-level agents, falling back to interaction-level agents.

**Frozen contract:** `agent_id`, `assisting_agent_id`, `billing_agent_id` on `ons.interaction` will NOT be removed when sessions are added. They record the INTAKE-TIME attribution. Session agents may differ.

### Q5: Where do legacy pipeline stages (12 canonical) map?

The legacy `v_customer_pipeline` view computes a pipeline stage from multiple table fields. In Odoo, this splits across entities:

| Legacy Stage | Odoo Entity | Odoo Field |
|-------------|-------------|------------|
| `intake_submitted` | ons.interaction | state=new |
| `triage_in_progress` | ons.interaction | state=classified, session_path=no_session |
| `callback_scheduled` | ons.case | stage=Open + linked callback activity |
| `online_session_started` | ons.session | pipeline_stage=in_session |
| `handoff_to_assisting` | ons.session | assisting_agent_id set, pipeline_stage=in_session |
| `repair_in_progress` | ons.session | pipeline_stage=troubleshooting (assisting tech working) |
| `ready_for_verification` | ons.session | pipeline_stage=awaiting_billing |
| `billing_in_progress` | ons.session | pipeline_stage=awaiting_billing + billing_agent assigned |
| `paid` | ons.session | pipeline_stage=paid |
| `closed_won` | ons.case | stage=Closed + payment_collected=True |
| `closed_lost` | ons.case | stage=Closed + outcome=no_sale |
| `onsite_dispatched` | ons.dispatch | dispatch_status=sent/assigned/confirmed/in_progress |

**Key insight:** The legacy "pipeline stage" is a COMPUTED virtual column across 3+ tables. The Odoo equivalent is NOT a single field — it is the combination of case stage + session pipeline_stage + dispatch status. A reporting view will reconstruct the 12-stage pipeline for backward compatibility.

### Q6: What happens to interactions with no partner resolution?

**Answer:** They remain valid records with `partner_id=False`.

- **Current behavior:** `action_resolve_customer()` is a manual button — agents press it to find/create the partner. It's not automatic on creation.
- **Design rationale:** Automatic resolution risks false matches (see doc 22). Manual resolution gives agents a chance to verify.
- **Workflow impact:** An interaction CAN be classified and assigned without a partner. The partner link is strongly encouraged but not required.
- **Future enhancement:** When `ons_ops_3cx` daemon creates interactions automatically, it will attempt phone-based resolution but flag low-confidence matches for human review.

---

## Interaction → Case Creation Contract (for Prompt 4)

When `ons_ops_cases` module is built, the following contract MUST be followed:

```python
# Pseudo-code for case creation from interaction
def action_create_case(self):
    """Called on ons.interaction when routing to service path."""
    for rec in self:
        if rec.case_id:
            raise UserError("Interaction already linked to a case.")
        if rec.lead_id:
            raise UserError("Interaction linked to a lead, not service path.")
        
        case = self.env['ons.case'].create({
            'partner_id': rec.partner_id.id,
            'primary_interaction_id': rec.id,
            'subject': rec.subject or rec.issue_description[:80],
            'assigned_agent_id': rec.agent_id.id,
            'priority': 'normal',
        })
        rec.case_id = case.id
        rec.state = 'assigned'
```

**Validation rules:**
1. `partner_id` SHOULD be set before case creation (warn if not)
2. `primary_driver_id` MUST be set (interaction must be classified first)
3. Case subject derived from interaction, not duplicated
4. Agent attribution flows from interaction to case

---

## Lead Creation Contract (for Prompt 4+)

```python
# Pseudo-code for lead creation from interaction  
def action_create_lead(self):
    """Called on ons.interaction when routing to CRM path."""
    for rec in self:
        if rec.lead_id:
            raise UserError("Interaction already linked to a lead.")
        if rec.case_id:
            raise UserError("Interaction linked to a case, not CRM path.")
        
        lead = self.env['crm.lead'].create({
            'name': f"Lead from {rec.name}",
            'partner_id': rec.partner_id.id,
            'phone': rec.customer_phone,
            'email_from': rec.customer_email,
            'interaction_id': rec.id,
            'description': rec.issue_description,
        })
        rec.lead_id = lead.id
        rec.state = 'assigned'
```

---

## State Transition Diagram (Full Lifecycle)

```
┌─────────────────────────────────────────────────────────────────┐
│                     ons.interaction                              │
│  [NEW] ──classify──▶ [CLASSIFIED] ──assign──▶ [ASSIGNED] ──▶ [COMPLETED]
│                          │                        │                     │
│                          │                   creates one of:           │
│                          │                   ┌─────────┐              │
│                          │                   │crm.lead │              │
│                          │                   └─────────┘              │
│                          │                        OR                  │
│                          │                   ┌──────────┐             │
│                          │                   │ons.case  │             │
│                          │                   │  ├session │             │
│                          │                   │  ├session │             │
│                          │                   │  └dispatch│             │
│                          │                   └──────────┘             │
│                          │                        OR                  │
│                          │                   (interaction-only)       │
└─────────────────────────────────────────────────────────────────┘
```
