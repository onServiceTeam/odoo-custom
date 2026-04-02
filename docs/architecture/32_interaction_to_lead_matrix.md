# 32 — Interaction → Lead Decision Matrix

**Date:** 2026-04-02  
**Purpose:** Define the exact decision logic for when/how an interaction produces a CRM lead, and what type of lead it becomes.

---

## 1. Decision Flowchart

```
Interaction Created (state=new)
        │
        ▼
  Is disposition == missed / abandoned / spam?
        │
     YES ──► STOP (no lead, interaction-only)
        │
       NO
        │
        ▼
  Is direction == internal?
        │
     YES ──► STOP (no lead, interaction-only)
        │
       NO
        │
        ▼
  Has interaction been classified?
  (state >= classified, primary_driver_id set)
        │
       NO ──► WAIT (classify first)
        │
      YES
        │
        ▼
  What is session_path?
        │
        ├─ not_applicable ──► STOP (no lead)
        │
        ├─ no_session ──► Is driver category billing/admin-only?
        │                    │
        │                 YES ──► STOP (interaction-only)
        │                    │
        │                  NO ──► Is caller returning/subscriber with renewal intent?
        │                            │
        │                         YES ──► CREATE lead_type=renewal
        │                            │
        │                          NO ──► STOP (or agent manually promotes to nurture)
        │
        ├─ callback ──► CREATE lead_type=callback_request
        │
        ├─ session_now ──► CREATE lead_type=service_lead
        │
        ├─ session_scheduled ──► CREATE lead_type=service_lead
        │
        └─ onsite_queue ──► CREATE lead_type=service_lead
```

---

## 2. Full Matrix

| session_path | disposition | direction | driver_category | caller_relationship | Lead Created? | lead_type |
|-------------|-------------|-----------|-----------------|--------------------:|:-------------:|-----------|
| session_now | answered | inbound | technical | first_time_lead | YES | service_lead |
| session_now | answered | inbound | technical | returning_no_plan | YES | service_lead |
| session_now | answered | inbound | technical | active_subscriber | YES | service_lead |
| session_now | answered | inbound | technical | past_subscriber | YES | service_lead |
| session_scheduled | answered | any | technical | any | YES | service_lead |
| onsite_queue | answered | any | any | any | YES | service_lead |
| callback | answered | inbound | any | any | YES | callback_request |
| callback | voicemail | inbound | any | any | YES | callback_request |
| no_session | answered | inbound | billing | any | NO | — |
| no_session | answered | inbound | admin | any | NO | — |
| no_session | answered | inbound | technical | returning/subscriber | YES* | renewal |
| no_session | answered | inbound | technical | first_time/past | NO** | — |
| not_applicable | any | any | any | any | NO | — |
| any | missed | any | any | any | NO | — |
| any | abandoned | any | any | any | NO | — |
| any | any | internal | any | any | NO | — |

\* Renewal leads are auto-created only when the caller is a returning customer or subscriber AND the driver indicates renewal/upsell interest.  
\** Agents may manually promote these to `nurture` leads via UI action.

---

## 3. Lead Field Population

When a lead is created from an interaction, these fields are auto-populated:

| Lead Field | Source |
|-----------|--------|
| `name` | `"[driver_name] - [partner_name or phone]"` |
| `interaction_id` | Source interaction |
| `partner_id` | From interaction's matched partner (may be empty) |
| `phone` | From interaction's `caller_phone` |
| `email_from` | From partner if resolved, else empty |
| `lead_type` | Per matrix above |
| `caller_relationship` | From partner's `customer_segment` mapping |
| `primary_driver_id` | From interaction's `primary_driver_id` |
| `callback_requested` | True if `lead_type=callback_request` |
| `user_id` | From interaction's `assigned_agent_id` |
| `type` | `'lead'` (not opportunity until qualified) |
| `stage_id` | Stock "New" (id=1) |
| `source_id` | Set to "Phone" source (or create if needed) |

---

## 4. Duplicate Prevention Rules

Before creating a lead, check for existing active leads:

1. **Same phone + same driver** → Existing active lead in pipeline (not won/lost)?
   - YES → Attach interaction to existing lead, do NOT create new
   - NO → Create new lead

2. **Same phone + different driver** → Always create new lead (different need)

3. **Same phone + existing lead is won/lost** → Create new lead (new opportunity)

"Active lead" means: `active=True` AND `stage_id.is_won=False` AND NOT in lost stages.

---

## 5. Manual Promotion Actions

Agents can manually create leads from interactions that didn't auto-generate one:

### `action_create_lead_from_interaction()`
Available on `ons.interaction` form when:
- Interaction has no linked lead yet
- Interaction state ≥ `classified`

Opens a wizard to select `lead_type` and confirm creation.

### `action_promote_to_nurture()`
Available on `crm.lead` when:
- lead_type ∈ (`inquiry`,) or no lead_type set
- Lead has contact info (phone or email)
- Lead is not lost/won

Sets `lead_type = 'nurture'`, marks `is_nurture_eligible = True`.

---

## 6. Caller Relationship Mapping

The `caller_relationship` field on `crm.lead` maps from the partner's `customer_segment`:

| partner.customer_segment | lead.caller_relationship |
|-------------------------|------------------------|
| `new` | `first_time_lead` |
| `returning` | `returning_no_plan` |
| `subscriber` | `active_subscriber` |
| `vip` | `active_subscriber` |
| (no partner) | `first_time_lead` (assumed) |

This matches the legacy `callContextPhase3.ts` classification exactly.

---

## 7. Stage Advancement Triggers

| Trigger | Stage Change |
|---------|-------------|
| Lead created | → New |
| Partner resolved + contact verified | → Qualified |
| Service quote discussed | → Proposition |
| Session started (Prompt 5) | → Won + convert to case |
| Customer declines | → Lost (with reason) |
| No response after N callbacks | → Lost ("No Response / Unreachable") |
