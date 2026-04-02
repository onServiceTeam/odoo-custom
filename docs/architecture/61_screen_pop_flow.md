# 61 — Screen-Pop Flow

## Current State

The legacy middleware provides screen-pop via a React frontend that polls
the `GET /api/3cx/active-calls` endpoint every 3 seconds. When a new
inbound call appears for the agent's extension, it shows a popup with:

- Caller number
- Customer profile (if matched)
- Recent case history
- Call driver guess
- "Log Call" / "Create Interaction" action

## Odoo Equivalent Architecture

### Phase 1 (This Prompt) — Data Foundation

1. **`ons.active.call`** model with ephemeral call records
2. **`ons.call.log`** model with permanent CDR
3. **`ons.user.extension`** for agent→extension mapping
4. **Server action** `action_create_interaction_from_call` on `ons.call.log`
   that creates an `ons.interaction` pre-populated with CDR metadata
5. **Partner resolution** helper that searches by normalized phone number

### Phase 2 (Future Prompt) — Live Frontend Widget

1. Owl component polling `ons.active.call` for current user's extension
2. Desktop notification on new inbound call
3. One-click "Open / Create Interaction" action
4. This is frontend JS work, deferred to a later prompt

### Screen-Pop Data Resolution Flow

```
Inbound call arrives at 3CX
        ↓
CDR sync polls recordings endpoint (15 min)
        ↓
ons.call.log created with:
  - cdr_primary_id
  - caller_number / callee_number
  - queue_name
  - agent_extension → user_id via ons.user.extension
  - disposition, duration, recording_url
        ↓
Partner resolution:
  normalize(caller_number) → last 10 digits
  search res.partner(phone/mobile = normalized)
  if exactly 1 → partner_id set
  if 0 → partner_id empty, marked as new_caller
  if >1 → partner_id empty, marked as ambiguous
        ↓
Agent opens call log (or is notified)
        ↓
Clicks "Create Interaction" action
        ↓
ons.interaction created with:
  - threecx_cdr_id = call_log.cdr_primary_id
  - partner_id, customer_phone, customer_name
  - call_start, call_end, call_duration, talk_duration
  - queue_name, disposition, has_recording, recording_url
  - interaction_type = phone, direction = call_log.direction
        ↓
Agent proceeds with intake workflow
```

## Ambiguity Handling

- Never silently assign wrong partner
- If >1 partner matches phone, show all candidates
- Agent makes final decision
- Logged as `match_status = 'ambiguous'` on the call log
