# 60 — Telephony Contract

## Overview

The 3CX integration provides telephony context for the onService Operations
Center. Legacy middleware polls 3CX XAPI for call recordings (15 min cycle),
active calls (3 s cycle), and agent status. There are **no 3CX webhooks** —
everything is polling-based.

## What Data Is Synced

| Source | Target | Method | Frequency |
|--------|--------|--------|-----------|
| 3CX XAPI `/activecalls` | `ons.active.call` | Polling | 3–5 s |
| 3CX XAPI `/recordings` | `ons.call.log` | Batch sync | 15 min |
| 3CX XAPI `/users` | `ons.user.extension` | Manual/admin | On demand |
| 3CX XAPI queue reports | Queue backfill on `ons.call.log` | Batch | After recording sync |

## What Is Realtime vs Periodic

### Realtime (sub-10 second)
- Active calls — needs a background sidecar/cron or external daemon
- Agent status — same sidecar that polls active calls

### Periodic (15 min batch)
- CDR / call logs — synced from recordings endpoint
- Queue backfill — corrects initial "Unspecified" queue from recordings
- Recording URL resolution

### On-demand
- Extension-user mapping — admin-managed or bulk sync
- Recording playback — proxied through server on request

## Odoo vs Sidecar Boundary

**In Odoo (models + views + cron):**
- `ons.call.log` — normalized CDR records, permanent history
- `ons.active.call` — ephemeral active call state (cleaned on end)
- `ons.agent.status` — current agent presence
- `ons.user.extension` — extension→user mapping
- Cron: 15-min CDR sync, queue backfill, daily recording cleanup
- Views: call log, active calls, extension admin, recording access

**Sidecar (future, NOT built in this prompt):**
- Sub-10-second polling loop for active calls/agent status
- This is better as a systemd-managed Python script or Odoo cron
  with very short interval, calling XAPI and writing to Odoo models
- For MVP: a 1-minute Odoo cron for active calls is acceptable;
  sub-second is deferred to a future sidecar prompt

## Partner/Case Matching Rules During Inbound Calls

1. Normalize caller number to last 10 digits
2. Search `res.partner` by `phone` or `mobile` matching normalized number
3. If exactly 1 match → auto-link
4. If 0 matches → leave unlinked (new caller)
5. If >1 match → mark as ambiguous, do NOT silently pick one
6. Link to the most recent open interaction for that partner's phone

## Screen-Pop Behavior

In the legacy system, screen-pop is a frontend feature. For Odoo:
1. Agent clicks "incoming call" notification (active call record)
2. System resolves partner from caller number
3. Opens partner form with call context, or shows "New Caller" banner
4. If partner has open case, shows case link
5. Creates new interaction pre-populated with call metadata

This is modeled as a server action + client-side call widget.
Full frontend screen-pop widget is deferred; the data model and
server actions are built now.

## Recording/Link Behavior

- Recording URL stored on `ons.call.log.recording_url`
- Playback proxied through a controller that adds 3CX auth token
- Recording also linked through `ons.interaction.recording_url`
  (populated when interaction is created from call log)
- Controller: `GET /ons_ops_3cx/recording/<call_log_id>`

## Extension/User Mapping

- `ons.user.extension` maps 3CX extension string → `res.users`
- One extension per user (unique constraint)
- Admin-managed via Configuration → Extensions
- Used during CDR sync to resolve `agent_extension` → Odoo user

## CDR Primary ID

- `cdr_primary_id` from 3CX XAPI is the unique identifier
- Also stored on `ons.interaction.threecx_cdr_id` for cross-reference
- Dedup: CDR sync skips records where `cdr_primary_id` already exists

## Products of This Prompt

- `ons.call.log` — permanent CDR normalized from 3CX
- `ons.active.call` — ephemeral active call state
- `ons.agent.status` — current agent presence slice
- `ons.user.extension` — extension↔user mapping
- Extension of `ons.interaction` — link to call log
- Cron jobs for periodic sync
- Views and menus under Operations
