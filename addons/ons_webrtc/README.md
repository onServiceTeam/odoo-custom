# ons_webrtc

**Version:** 19.0.1.0.0  
**License:** LGPL-3  
**Depends:** mail  

## Purpose

Configuration and health monitoring for WebRTC infrastructure:
- Admin-only health check endpoint for SFU and ICE servers
- Verifies SFU reachability via TCP socket check
- Reports ICE server count from `mail.ice.server`

## Routes

| Route | Auth | Purpose |
|-------|------|---------|
| `/ons_webrtc/health` | admin | Check SFU reachability + ICE server count |

## Infrastructure

- **SFU**: Odoo SFU service at `mail.sfu_server_url` config parameter
- **TURN/STUN**: Configured via Odoo's `mail.ice.server` model
- **coturn**: External TURN server (port 3478)

## Upgrade Notes

| Risk | Component | Detail |
|------|-----------|--------|
| LOW | Health controller | Standalone endpoint, no stock overrides |
| LOW | No models | Config-only addon, reads existing `mail.*` parameters |

## Testing

```bash
docker exec odoo-web odoo -d test_db -i ons_webrtc --test-enable --stop-after-init --no-http
```
