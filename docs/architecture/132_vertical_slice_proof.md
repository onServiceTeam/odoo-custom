# 132 — Vertical Slice Proof

> Executed: 2025-07-02 against `onservice_test_db`
> Result: **33 / 33 checks passed**

## Purpose

Prove one complete end-to-end workflow through the Odoo custom build:
from an inbound phone call to a closed, paid case.  This is the single
most important test — if this path works, the core system works.

---

## Scenario

**Karen White** calls the main line.  Chrome is hijacked by a popup scam
("Your computer is infected — call Microsoft").  She's afraid her bank
info was stolen.  Agent takes the call, classifies it, starts a remote
session, removes the malware, bills for Advanced Repair + Data Backup,
collects payment, and closes the case as won.

---

## Step-by-Step Results

### Step 1 — Create Customer
```
✅ res.partner #67 created
   Name: Karen White | Phone: +1 (561) 555-0199
   Segment: new | City: West Palm Beach FL 33401
```

### Step 2 — Log Inbound Interaction
```
✅ INT-260402-0112 created
   Type: phone/inbound | State: classified
   Driver: HACKED_POPUP_SCAM | Urgency: high
   Session path: session_now
   Call duration: 7 min (420s) | Talk: 6:20 (380s)
```

### Step 3 — Create CRM Lead
```
✅ crm.lead #22 created
   Name: "Karen White — Popup Scam Removal"
   interaction_id → INT-260402-0112 ✓
   partner_id → Karen White ✓
   is_convertible = True ✓   (has partner + service-path interaction)
```
Bidirectional link set: `interaction.lead_id = lead.id` so
`action_convert_to_case()` can find the interaction.

### Step 4 — Convert Lead → Case
```
✅ crm.lead.action_convert_to_case() succeeded
   Case: CASE-2604-0008

   Verified links:
     case.partner_id          → Karen White       ✓
     case.source_interaction_id → INT-260402-0112 ✓
     case.lead_id             → crm.lead #22      ✓
     case.primary_driver_id   → HACKED_POPUP_SCAM ✓
     case.online_session_started = True            ✓

   Initial stage: online_session_started           ✓
   (auto-advanced from intake_submitted because session_path=session_now)
```

### Step 5 — Walk Through Pipeline
```
Allowed transition path:
  online_session_started → repair_in_progress → ready_for_verification → billing_in_progress

✅ Stage → repair_in_progress     (Tech starts repair)
✅ Stage → ready_for_verification  (Repair done, verifying)
✅ Stage → billing_in_progress     (Billing agent processes)

Each transition:
  - Validated against ALLOWED_TRANSITIONS matrix
  - Created ons.case.stage.history entry
  - Closed previous history entry (exited_at set)
```

### Step 6 — Add Billing Lines
```
✅ Line 1: ADVANCED_REPAIR  1 × $149.99
✅ Line 2: DATA_BACKUP      1 × $79.99
✅ amount_total = $229.98 (computed field)
✅ 2 billing lines on case
```

### Step 7 — Record Payment
```
✅ payment_status = paid
✅ payment_amount = $229.98
✅ Stage → paid (billing_in_progress → paid allowed)
```

### Step 8 — Close Case
```
✅ Stage → closed_won (paid → closed_won allowed)
✅ is_closed = True (related from stage)
✅ is_won = True (related from stage)
```

### Step 9 — Audit Trail
```
✅ 7 stage history entries recorded:
   Online Session Started → Intake Submitted → Repair In Progress →
   Ready for Verification → Billing In Progress → Paid → Closed — Won

   Each entry has: stage_id, entered_at, exited_at (except last), user_id
```

### Step 10 — Global Counters
```
✅ Total cases: 8      (6 demo + 1 failed test + 1 slice)
✅ Total interactions: 13
✅ Total leads: 8
✅ Closed/won cases: 2
✅ Partner interaction_count: 1
```

---

## What This Proves

| Capability | Status |
|-----------|--------|
| Customer creation with segments | ✅ Working |
| Interaction logging with driver codes | ✅ Working |
| CRM lead with is_convertible gating | ✅ Working |
| Lead → Case conversion (action_convert_to_case) | ✅ Working |
| Auto-advance on session_now path | ✅ Working |
| Stage transition validation (ALLOWED_TRANSITIONS) | ✅ Working |
| Stage history audit trail | ✅ Working |
| Billing line creation with product links | ✅ Working |
| Computed amount_total | ✅ Working |
| Payment status tracking | ✅ Working |
| Case closure lifecycle (is_closed, is_won) | ✅ Working |
| Counters and relational integrity | ✅ Working |

## What This Does NOT Test (future work)

- Odoo UI form submission (tested via RPC, not browser)
- Chatter / mail.thread message logging (framework-level)
- Portal customer view
- Report generation (agent_daily, queue_daily)
- AI/QA evaluation workflow
- Dispatch full lifecycle with dispatch.checklist
- SMS/Email thread creation from case
- Notification rule triggers
