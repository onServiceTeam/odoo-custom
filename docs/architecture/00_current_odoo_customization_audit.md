# 00 — Current Odoo Customization Audit

**Date:** 2026-04-01  
**Odoo Version:** 19.0-20260324 (Community)  
**Server:** Hetzner VPS 46.62.207.225, Ubuntu 24.04.3 LTS  
**Database:** onservice_prod_db (PostgreSQL 18)  

## Scope

Audited all files in the Odoo container's core addons (`mail`, `discuss`, `web`, `bus`)
for local modifications, and all files in `/home/onservice/odoo-custom/addons/`.

## Findings

### Core Edits: NONE

Verified zero local modifications to upstream Odoo code:
- `mail/` — no changes
- `web/` — no changes  
- `bus/` — no changes
- No `discuss/` addon exists separately in Odoo 19 (it's part of `mail`)

All Discuss customizations were already isolated in the `discuss_thread_admin` custom addon.

### Custom Addons Inventory

| Addon | Version | Status | Description |
|-------|---------|--------|-------------|
| `discuss_thread_admin` | 19.0.6.0.0 | Meta-package | Installs all ons_* addons |
| `ons_discuss_ui` | 19.0.1.0.0 | Installed | Discord theme, work status, sidebar config |
| `ons_discuss_threads` | 19.0.1.0.0 | Installed | Thread admin, intake, reorder |
| `ons_discuss_voice` | 19.0.1.0.0 | Installed | Voice channels, RTC overrides |
| `ons_gif_provider` | 19.0.1.0.0 | Installed | GIPHY replacement for Tenor |
| `ons_webrtc` | 19.0.1.0.0 | Installed | WebRTC health check |

### External Services

| Service | Status | Config |
|---------|--------|--------|
| coturn (TURN/STUN) | Running | Port 3478, user `odoo` |
| Odoo SFU | Running | Port 8070 |
| GIPHY API | Active | Key in `discuss.giphy_api_key` |
| SMTP | Active | `mail.onservice.us:587` STARTTLS |

## Conclusion

The installation is clean — no core debt exists. All customizations live in the
`ons_*` addon layer. This is the ideal starting state for building additional
modules and for future Odoo upgrades.
