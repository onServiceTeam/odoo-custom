# 41 — Stage Transition Matrix

**Date:** 2026-04-02  
**Purpose:** Define all allowed stage transitions, triggers, and validation rules for `ons.case`.

---

## 1. Transition Graph

```
                                    ┌──────────────────────┐
                                    │   onsite_dispatched   │
                                    │        (12)           │
                                    └──────────┬───────────┘
                                               │ (can return to repair_in_progress)
                                               ▼
intake_submitted ──► triage_in_progress ──► callback_scheduled ──► session_started
      (1)                 (2)                    (3)                    (4)
                                                                        │
                                                                        ▼
                                                              handoff_to_tech
                                                                    (5)
                                                                        │
                                                                        ▼
                                                              repair_in_progress
                                                                    (6)
                                                                        │
                                                                        ▼
                                                          ready_for_verification
                                                                    (7)
                                                                        │
                                                                        ▼
                                                          billing_in_progress
                                                                    (8)
                                                                        │
                                                                        ▼
                                                                    paid
                                                                    (9)
                                                                        │
                                                                        ▼
                                                                closed_won
                                                                   (10)

Any active stage ──────────────────────────────────────────► closed_lost (11)
```

---

## 2. Allowed Transitions

| From | To | Trigger | Validation |
|------|----|---------|------------|
| `intake_submitted` | `triage_in_progress` | Agent begins triage | — |
| `intake_submitted` | `session_started` | Direct session start (skip triage) | — |
| `intake_submitted` | `callback_scheduled` | Callback set | — |
| `intake_submitted` | `onsite_dispatched` | Immediate onsite need | — |
| `triage_in_progress` | `callback_scheduled` | Callback set during triage | — |
| `triage_in_progress` | `session_started` | Session starts | — |
| `triage_in_progress` | `onsite_dispatched` | Onsite needed | — |
| `callback_scheduled` | `session_started` | Callback completed, session begins | — |
| `callback_scheduled` | `triage_in_progress` | Callback reveals more triage needed | — |
| `session_started` | `handoff_to_tech` | Agent hands off to tech | `assigned_tech_id` required |
| `session_started` | `repair_in_progress` | Same agent does repair | — |
| `handoff_to_tech` | `repair_in_progress` | Tech begins work | — |
| `repair_in_progress` | `ready_for_verification` | Repair done, needs VBT | — |
| `repair_in_progress` | `onsite_dispatched` | Remote can't fix, onsite needed | — |
| `ready_for_verification` | `billing_in_progress` | VBT begins billing | `billing_agent_id` recommended |
| `billing_in_progress` | `paid` | Payment received | — |
| `paid` | `closed_won` | Case completed | — |
| `onsite_dispatched` | `repair_in_progress` | Onsite completes, back to repair flow | — |
| `onsite_dispatched` | `ready_for_verification` | Onsite done, ready for VBT | — |
| ANY active | `closed_lost` | Declined / cancelled / not serviceable | Requires reason |
| `closed_won` | `intake_submitted` | Reopen (manager only) | Manager group required |
| `closed_lost` | `intake_submitted` | Reopen (manager only) | Manager group required |

---

## 3. Transitions NOT Allowed

| From | To | Why |
|------|----|-----|
| `paid` | Any except `closed_won` | Once paid, only completion |
| `closed_won` | `closed_lost` | Won is terminal in one direction |
| backward through session stages | earlier stages | No skipping backward except reopen |

**Backward movement** is only allowed for:
- `callback_scheduled` → `triage_in_progress` (callback reveals new info)
- `onsite_dispatched` → `repair_in_progress` or `ready_for_verification` (onsite done)
- Reopen from terminal → `intake_submitted` (manager only)

---

## 4. Stage History Logging

Every stage change creates an `ons.case.stage.history` record:

| Field | Type | Purpose |
|-------|------|---------|
| `case_id` | Many2one → ons.case | Parent case |
| `stage_id` | Many2one → ons.case.stage | Stage entered |
| `entered_at` | Datetime | When this stage was entered |
| `exited_at` | Datetime | When this stage was left (null if current) |
| `duration_hours` | Float | Computed: (exited_at - entered_at) / 3600 |
| `user_id` | Many2one → res.users | Who triggered the transition |
| `is_override` | Boolean | True if manager manually forced stage |
| `notes` | Text | Optional reason for transition |

---

## 5. Time-in-Stage Calculations

| Metric | Computation |
|--------|-------------|
| Current stage duration | `now() - current_history.entered_at` |
| Total time in any past stage | Sum of `duration_hours` for that stage in history |
| Bottleneck detection | Any stage > 4 hours triggers "stale" flag |
| Leakage detection | Cases that skip stages (e.g., intake → paid) flagged for audit |

---

## 6. Overdue / Stale Rules

| Condition | Flag |
|-----------|------|
| Hours in pipeline > 24 | `is_stale = True` |
| Stage unchanged > 4 hours AND stage is active work (4–8) | `needs_attention = True` |
| Payment status = for_collection | `is_overdue = True` (Prompt 6) |
| Callback scheduled > 2 hours past due | `callback_overdue = True` |
