# 70 — Dispatch Contract

> Authored during Prompt 8.  Source of truth: legacy
> `script-secure-guard-8285b830` dispatch subsystem.

---

## 1. When a case becomes a dispatch candidate

| Rule | Source |
|------|--------|
| `ons.case.stage.code == 'onsite_dispatched'` | Legacy `session_path = 'ONSITE_QUEUE'` |
| No existing dispatch linked to the case | Legacy `WHERE wa.id IS NULL` |
| `partner_id` required on case | Denormalized customer fields needed for dispatch |
| Address is populated (street, city, state, zip) | Legacy requires Google Places validation before WM send |

A dispatch can also be created **independently** (from customer search
or manual entry) without a parent case — but the primary path is
case-driven.

---

## 2. What a dispatch record owns

The `ons.dispatch` model owns the full onsite visit lifecycle:

| Field Group | Fields |
|-------------|--------|
| **Identity** | name (sequence), case_id, partner_id, title, description |
| **Location** | street, street2, city, state_id, zip, country_id, location_type, address_validated, lat, lng |
| **Contact** | contact_first_name, contact_last_name, contact_phone, contact_extension |
| **Schedule** | scheduled_start, scheduled_end, customer_timezone |
| **Pricing** | budget, pricing_type, payment_terms |
| **Assignment** | assigned_worker_name, assigned_worker_id |
| **Lifecycle timestamps** | confirmed_at, started_at, completed_at, cancelled_at, voided_at |
| **Cancellation** | cancellation_reason, void_reason |
| **External** | wm_assignment_id (future WorkMarket reference) |
| **Approval** | requires_approval, approved_by, approved_at |

---

## 3. Dispatch status state machine

```
draft ──→ pending_approval ──→ sent ──→ has_applicants ──→ assigned ──→ confirmed ──→ in_progress ──→ completed
  │              │                │            │               │             │               │
  ├→ cancelled   ├→ cancelled     ├→ cancelled ├→ cancelled    ├→ cancelled  ├→ cancelled    └→ cancelled
  ├→ voided      ├→ voided        ├→ voided    ├→ voided       ├→ voided     ├→ voided
  └→ sent        └→ sent
```

Terminal statuses: `completed`, `cancelled`, `voided`.

See `71_dispatch_state_matrix.md` for the full transition table.

---

## 4. What reminders exist

Legacy defines 7 standard intervals, each with per-channel toggles:

| Minutes Before | Discord | SMS | Email | Voice |
|---------------|---------|-----|-------|-------|
| 1440 (24h)   | ✓ | — | — | — |
| 120 (2h)     | ✓ | ✓ | — | — |
| 45           | ✓ | — | — | — |
| 30           | ✓ | — | — | — |
| 15           | ✓ | ✓ | — | — |
| 10           | ✓ | — | — | — |
| 5            | ✓ | — | — | — |

In the Odoo build, we model:
- `ons.dispatch.reminder` instances per dispatch with fire times
- Reminder configs as data records
- Channel delivery tracking (sent/error per channel)
- Retry logic (max 3, with backoff)

Actual channel delivery (SMS/email/voice integration) is a future
concern — this prompt builds the **data structure and scheduling
foundation**.

---

## 5. What applicant logic exists

Legacy uses WorkMarket offers/applicants:
- `ons.dispatch.applicant` tracks workers who apply to the assignment
- Statuses: `pending`, `accepted`, `rejected`, `withdrawn`
- Accept/reject are WM API operations; locally tracked
- Only ONE applicant can be accepted per dispatch at a time
- Offer ID (not worker ID) is the API key for accept/reject

In the Odoo build, we represent applicants as local records linked
to the dispatch.  Actual WM API calls are future — this prompt
builds the **data layer and workflow**.

---

## 6. What voice confirmation/cancellation flows exist

Legacy DTMF menu on customer voice reminders:
- `1` = Confirm appointment → status `confirmed`
- `2` = Cancel → asks for cancellation reason (5 DTMF sub-choices)
- `3` = Reschedule → outcome `reschedule_requested` (manual review)
- `0` = Transfer to agent → Returning Caller queue
- `*` = Replay message

Voice outcomes:
- `confirmed`, `cancelled`, `reschedule_requested`,
  `voicemail_left`, `no_answer`, `failed`, `transferred`, `skipped`

Cancellation reasons (mapped to DTMF 1-5):
- `CUST_SCHEDULE`, `CUST_NOT_NEEDED`, `CUST_ALTERNATIVE`,
  `CUST_COST`, `CUST_OTHER`

In the Odoo build, we model `ons.dispatch.voice.call` with outcome
tracking. Actual 3CX/Twilio voice execution is future — this prompt
builds the **data model and outcome recording**.

---

## 7. What future external integrations connect here

| Integration | Status in Prompt 8 |
|-------------|-------------------|
| WorkMarket API | **Data model only** — wm_assignment_id stored, no live API calls |
| Google Places (address validation) | **Data model only** — address_validated flag, lat/lng fields |
| Twilio SMS (reminders) | **Data model only** — SMS channel flags on reminders |
| 3CX/Twilio Voice | **Data model only** — voice call records with outcomes |
| Discord notifications | **Data model only** — dispatch_status triggers |

---

## 8. Checklist system

Default pre-dispatch checklist items:

| Code | Name | Required |
|------|------|----------|
| `tech_called` | Call Onsite Technician | YES |
| `customer_contacted` | Contact Customer | YES |
| `address_verified` | Verify Address | YES |
| `schedule_confirmed` | Confirm Schedule | YES |
| `payment_discussed` | Discuss Payment | NO |
| `special_instructions` | Special Instructions | NO |

Items are created per-dispatch from config. Required items must be
completed for dispatch readiness validation.

---

## 9. Activity log

Every action on a dispatch is logged in `ons.dispatch.activity.log`:
- status changes, applicant decisions, reminder events, voice outcomes,
  checklist completions, manual notes, approval actions.
