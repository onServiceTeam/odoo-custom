# 62 — Realtime vs Sync Boundary

## Design Principle

Separate concerns cleanly:
- **Permanent CDR** — `ons.call.log` — batch-synced every 15 min from 3CX recordings
- **Ephemeral active state** — `ons.active.call` / `ons.agent.status` — short-lived,
  refreshed by polling, cleaned up automatically

## Sync Architecture

### Layer 1: CDR Batch Sync (15 min cron)

```
3CX XAPI /recordings
    → filter by time window (last sync + safety overlap)
    → normalize fields (phone, queue, extension, duration)
    → dedup by cdr_primary_id
    → create/update ons.call.log records
    → run partner resolution
    → run queue backfill from queue reports
```

**Odoo Implementation:** `ir.cron` running `ons.call.log._cron_sync_from_3cx()`

### Layer 2: Active Call Polling (1 min cron for MVP)

```
3CX XAPI /activecalls
    → upsert ons.active.call by threecx_call_id
    → remove ended calls not in active list
    → resolve user from agent_extension
```

**Odoo Implementation:** `ir.cron` running `ons.active.call._cron_sync_active_calls()`

For sub-10-second polling, a future sidecar/daemon will replace this cron.

### Layer 3: Agent Status (piggybacks on active call sync)

```
3CX XAPI /users
    → map extension to ons.user.extension
    → update ons.agent.status (Available, OnCall, DND, Away, etc.)
```

## 3CX XAPI Credentials

Stored in `ir.config_parameter`:
- `ons_ops_3cx.host` — e.g., `onservice.3cx.us`
- `ons_ops_3cx.client_id`
- `ons_ops_3cx.client_secret`

OAuth token cached in transient model or `ir.config_parameter`
with expiry tracking.

## Data Retention

- `ons.call.log` — permanent, mirrors legacy `call_logs` table
- `ons.active.call` — cleaned every sync cycle; records older than 1 hour purged
- `ons.agent.status` — current state only; history not stored (defer to future reporting)

## Queue Backfill

3CX recordings API returns `queue_name = 'Unspecified'` for many calls.
The actual queue is only available from XAPI queue reports endpoint.
After recording sync, a second pass queries queue reports and updates
`ons.call.log.queue_name` where it was 'Unspecified'.

## Error Handling

- 3CX API unavailable → log warning, skip cycle, retry next cron run
- Token expired → clear cache, re-authenticate, retry once
- Partial sync failure → committed records stay, failed records retried next cycle
- No destructive rollback of previously synced records

## Future Sidecar

When sub-second screen-pop is needed:
1. Python daemon with `while True` loop polling 3CX every 3 seconds
2. Writes directly to `ons.active.call` and `ons.agent.status` via XML-RPC
3. Managed by systemd, deployed alongside Odoo
4. Odoo cron disabled when sidecar is active
5. Configuration: `ons_ops_3cx.use_sidecar` boolean parameter
