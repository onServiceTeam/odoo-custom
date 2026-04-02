# 31 — Consent Model and Rules

**Date:** 2026-04-02  
**Purpose:** Specify the `ons.contact.consent` model, state machine, and business rules that govern opt-in/opt-out across all channels.

---

## 1. Problem Statement

Legacy has only:
- `consentVerified: boolean` on voice calls (single flag, no channel/scope detail)
- `dispatch_cancellation_reasons` table (DTMF-based decline tracking, not true consent)

The business needs per-channel, per-scope consent with an audit trail to:
- Comply with TCPA (phone/SMS), CAN-SPAM (email), and state privacy laws
- Track explicit opt-in/opt-out per contact method
- Distinguish marketing consent from operational consent
- Never lose consent history (immutable audit log)

---

## 2. Model Definition: `ons.contact.consent`

### Fields

| Field | Type | Required | Default | Notes |
|-------|------|----------|---------|-------|
| partner_id | Many2one → res.partner | YES | — | Consent is per-customer |
| channel | Selection | YES | — | `email` / `sms` / `phone` / `any` |
| scope | Selection | YES | — | `marketing` / `operational` / `callback` / `renewal` / `service_terms` |
| status | Selection | YES | `pending` | `pending` / `opted_in` / `double_opted_in` / `opted_out` / `revoked` |
| capture_source | Selection | YES | — | `web_form` / `phone_call` / `email_reply` / `sms_reply` / `manual` |
| captured_by_id | Many2one → res.users | NO | current user | Agent who recorded |
| interaction_id | Many2one → ons.interaction | NO | — | If captured during a call |
| opted_in_at | Datetime | NO | — | Set when status → opted_in |
| confirmed_at | Datetime | NO | — | Set when status → double_opted_in |
| opted_out_at | Datetime | NO | — | Set when status → opted_out |
| revoked_at | Datetime | NO | — | Set when status → revoked (compliance) |
| evidence | Text | NO | — | Free text: proof of consent |
| active | Boolean | NO | True | Archive support |

### Mixins

- `mail.thread` — full chatter for audit trail
- NO `mail.activity.mixin` — consent records don't need scheduled activities

### Unique Constraint

One active consent per `(partner_id, channel, scope)`. Enforced via SQL unique partial index on
`(partner_id, channel, scope) WHERE active = true`.

---

## 3. State Machine

```
pending ──► opted_in ──► double_opted_in
   │            │                │
   │            ▼                ▼
   │         opted_out       opted_out
   │            │                │
   ▼            ▼                ▼
 opted_out   (terminal)      (terminal)
   │
   ▼
(terminal)
```

### Transition Rules

| From | To | Allowed? | Side Effects |
|------|----|----------|-------------|
| pending | opted_in | YES | Set `opted_in_at` |
| pending | opted_out | YES | Set `opted_out_at` |
| opted_in | double_opted_in | YES | Set `confirmed_at` |
| opted_in | opted_out | YES | Set `opted_out_at` |
| double_opted_in | opted_out | YES | Set `opted_out_at` |
| any | revoked | YES (admin only) | Set `revoked_at`, archive record |
| opted_out | any | NO | Terminal. Create new record to re-consent. |
| revoked | any | NO | Terminal. Create new record to re-consent. |

### Re-Consent After Opt-Out

When a customer opts back in after opting out:
1. The old consent record stays archived (audit trail)
2. A NEW consent record is created with `status=opted_in`
3. The old record's `active=False` satisfies the unique constraint

---

## 4. Security Rules

| Group | Create | Read | Write | Unlink |
|-------|--------|------|-------|--------|
| Agent (ons_ops_core.group_ops_agent) | YES | YES (own interactions) | YES (status transitions only) | NO |
| Manager (ons_ops_core.group_ops_manager) | YES | YES (all) | YES | NO |
| Admin (ons_ops_core.group_ops_admin) | YES | YES (all) | YES + revoke | NO |

**Consent records are NEVER deleted.** Only archived via `active=False`.

---

## 5. Business Actions

### `action_opt_in()`
- Validates status ∈ (`pending`,)
- Sets `status = 'opted_in'`, `opted_in_at = now()`

### `action_confirm()`
- Validates status ∈ (`opted_in`,)
- Sets `status = 'double_opted_in'`, `confirmed_at = now()`

### `action_opt_out()`
- Validates status ∈ (`pending`, `opted_in`, `double_opted_in`)
- Sets `status = 'opted_out'`, `opted_out_at = now()`

### `action_revoke()` (admin only)
- Sets `status = 'revoked'`, `revoked_at = now()`, `active = False`
- Logs reason in chatter

---

## 6. Helper Methods on `res.partner`

### `has_consent(channel, scope)`
Returns `True` if partner has an active consent with status ∈ (`opted_in`, `double_opted_in`) for the given channel+scope.

### `consent_ids`
One2many computed field listing all consent records for the partner.

---

## 7. Integration Points

| System | How Consent Is Used |
|--------|-------------------|
| **Lead nurture** | `is_nurture_eligible` computed field on crm.lead checks `partner.has_consent('email', 'marketing')` |
| **Callback scheduling** (Prompt 5+) | Verify `partner.has_consent('phone', 'callback')` before scheduling |
| **Email campaigns** (Prompt 10+) | Filter by `has_consent('email', 'marketing')` |
| **SMS notifications** (future) | Filter by `has_consent('sms', 'operational')` |

---

## 8. Audit Requirements

1. Every status change logs a message to chatter (mail.thread)
2. The `evidence` field captures HOW consent was obtained (e.g., "Customer verbally agreed during call #123")
3. Timestamps are immutable once set (write-once pattern enforced in Python)
4. Consent records appear on the partner form under a dedicated tab
