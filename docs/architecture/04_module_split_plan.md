# 04 — Module Split Plan

**Date:** 2026-04-01  
**Status:** Phase 0 (Discuss extraction) COMPLETE. Phase 1+ modules planned.

## Current Modules (Phase 0 — Deployed)

| Module | Purpose | Models | Routes | JS Files | SCSS |
|--------|---------|--------|--------|----------|------|
| `ons_discuss_ui` | Theme, work status, sidebar config | res.config.settings, res.users | 2 | 4 | 2 |
| `ons_discuss_threads` | Thread admin, intake, reorder | discuss.channel, discuss.intake | 8 | 7 | 0 |
| `ons_discuss_voice` | Voice channels, RTC overrides | discuss.channel, discuss.channel.rtc.session | 1 | 2 | 0 |
| `ons_gif_provider` | GIPHY integration | res.config.settings, res.users | 3 (override) | 1 | 0 |
| `ons_webrtc` | WebRTC health check | (none) | 1 | 0 | 0 |
| `discuss_thread_admin` | Meta-package | (none) | 0 | 0 | 0 |

## Planned Modules (Phase 2–4 — Not Yet Built)

These modules will be built in order after the architecture spec (Prompt 1) is
completed. The names and responsibilities below are from the master playbook and
will be refined during Phase 2.

| Module | Purpose | Depends On | Priority |
|--------|---------|------------|----------|
| `ons_ops_shell` | Left-nav operations center, custom home | web | Phase 3 — first |
| `ons_ops_core` | Shared models: interaction, consent, customer | base | Phase 4.1 |
| `ons_ops_crm` | Lead/prospect/nurture flow | crm, ons_ops_core | Phase 4.2 |
| `ons_ops_intake` | Inbound call/message intake | ons_ops_core, ons_discuss_threads | Phase 4.3 |
| `ons_ops_cases` | Service cases / helpdesk | ons_ops_core | Phase 4.4 |
| `ons_ops_discuss` | Case-to-Discuss automation | mail, ons_ops_cases | Phase 4.5 |
| `ons_ops_3cx` | 3CX call sync, overlays | ons_ops_core | Phase 4.6 |
| `ons_ops_dispatch` | Dispatch + WorkMarket | ons_ops_cases | Phase 4.7 |
| `ons_ops_comms` | Email/SMS shared inbox | mail, ons_ops_core | Phase 4.8 |
| `ons_ops_ai` | AI intake, QA, summarization | ons_ops_core | Phase 4.9 |
| `ons_ops_reports` | Dashboards, metrics | ons_ops_core | Phase 4.10 |
| `ons_ops_portal` | Customer portal | portal, ons_ops_core | Phase 4.11 |
| `ons_ops_billing` | Payment + completion | account, ons_ops_core | Phase 4.12 |
| `ons_ops_subscriptions` | Subscriptions / contracts | ons_ops_billing | Phase 4.12 |

## Compatibility Addons (If Needed)

| Module | Purpose | When to Create |
|--------|---------|---------------|
| `mail_compat` | Bridge for mail behavior changes | Only if a stock mail change blocks our addons |
| `web_compat` | Bridge for web client changes | Only if a stock web change blocks our addons |
| `portal_compat` | Bridge for portal behavior | Only if stock portal changes break ons_ops_portal |
| `helpdesk_compat` | Bridge for OCA helpdesk | Only if OCA helpdesk model changes conflict |

## OCA Modules Under Consideration

| OCA Repo | Module | Purpose |
|----------|--------|---------|
| oca-helpdesk | helpdesk_mgmt | Base helpdesk if we don't build fully custom |
| oca-field-service | fieldservice | Onsite dispatch if WorkMarket bridge is complex |
| oca-contract | contract | Subscription/recurring billing |
| oca-dms | dms | Document management |
| oca-knowledge | knowledge | Knowledge base for agents |

## Enterprise Considerations

All `ons_*` module names are prefixed to avoid collision with Odoo Enterprise
module names. No `ons_*` model names collide with known Enterprise models.

If Enterprise is added later:
- Enterprise's `helpdesk` module may overlap with `ons_ops_cases` — evaluate whether to use Enterprise helpdesk and build a bridge, or keep custom
- Enterprise's `voip` module may overlap with `ons_ops_3cx` — our 3CX integration is specific enough that both can coexist
- Enterprise's `documents` module may overlap with OCA `dms` — choose one at that point
