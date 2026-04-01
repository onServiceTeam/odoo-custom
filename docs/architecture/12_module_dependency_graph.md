# 12 — Module Dependency Graph

**Date:** 2026-04-01  

---

## Complete Module Map

```
                        ┌───────────────────────────────────┐
                        │           Odoo Stock              │
                        │  base, mail, web, crm, account,   │
                        │  product, contacts, calendar       │
                        └────────────────┬──────────────────┘
                                         │
            ┌────────────────────────────┼────────────────────────────┐
            │                            │                            │
 ┌──────────▼──────────┐  ┌─────────────▼──────────┐  ┌─────────────▼──────────┐
 │   ons_discuss_ui    │  │    ons_gif_provider    │  │      ons_webrtc        │
 │  theme, work status │  │  GIPHY integration     │  │  health check only     │
 │  sidebar config     │  │                        │  │                        │
 └──────────┬──────────┘  └────────────────────────┘  └────────────────────────┘
            │
 ┌──────────▼──────────┐
 │ ons_discuss_threads  │
 │ thread admin, intake │
 │ reorder, delete      │
 └──────────┬──────────┘
            │
 ┌──────────▼──────────┐
 │  ons_discuss_voice   │
 │ voice channels, RTC  │
 └──────────────────────┘

            ┌────────────────────────────────────────────────────────┐
            │                  discuss_thread_admin                   │
            │              (meta-package: installs all above)         │
            └────────────────────────────────────────────────────────┘



 ═══════════════════════ PHASE 2-4 (Planned) ═══════════════════════

                        ┌───────────────────────────────────┐
                        │           Odoo Stock              │
                        │  base, mail, web, crm, account    │
                        └────────────────┬──────────────────┘
                                         │
                              ┌──────────▼──────────┐
                              │    ons_ops_core     │
                              │  ons.interaction    │
                              │  ons.call.driver    │
                              │  partner extensions │
                              │  shared utilities   │
                              └──────────┬──────────┘
                                         │
          ┌──────────────┬───────────────┼───────────────┬──────────────┐
          │              │               │               │              │
 ┌────────▼────────┐ ┌──▼───────────┐ ┌─▼────────────┐ │   ┌──────────▼───────┐
 │  ons_ops_crm    │ │ ons_ops_     │ │ ons_ops_     │ │   │  ons_ops_comms   │
 │  lead scoring,  │ │ intake       │ │ cases        │ │   │  email, SMS,     │
 │  nurture        │ │ call form,   │ │ case model,  │ │   │  shared inbox    │
 │  (extends crm)  │ │ AI classify  │ │ sessions,    │ │   │  reminders       │
 └─────────────────┘ │ 3CX trigger  │ │ kanban       │ │   └──────────────────┘
                      └──────────────┘ └──────┬───────┘ │
                                              │         │
                              ┌────────────────┤    ┌───▼────────────┐
                              │                │    │  ons_ops_3cx   │
                     ┌────────▼───────┐  ┌─────▼──┐│ 3CX sync,     │
                     │ ons_ops_       │  │ons_ops_││ realtime       │
                     │ dispatch       │  │ ai     ││ queues, agents │
                     │ on-site,       │  │ AI QA, │└────────────────┘
                     │ WorkMarket     │  │ grade, │
                     │ voice callback │  │ summary│
                     └────────────────┘  └────────┘

                              ┌──────────────────────┐
                              │   ons_ops_shell      │
                              │  left-nav cockpit    │
                              │  replaces stock menu │
                              │  depends: ALL above  │
                              └──────────────────────┘

                              ┌──────────────────────┐
                              │   ons_ops_reports    │
                              │  dashboards, KPIs    │
                              │  depends: ALL above  │
                              └──────────────────────┘
```

---

## Module Responsibility Matrix

### Tier 1 — Already Built (Phase 0)

| Module | Depends | Models | Purpose |
|--------|---------|--------|---------|
| `ons_discuss_ui` | mail | res.config.settings, res.users | Theme, work status, sidebar config |
| `ons_discuss_threads` | mail, ons_discuss_ui | discuss.channel, discuss.intake | Thread admin, intake, reorder |
| `ons_discuss_voice` | mail, ons_discuss_threads | discuss.channel, discuss.channel.rtc.session | Voice channels |
| `ons_gif_provider` | mail | res.config.settings, res.users | GIPHY integration |
| `ons_webrtc` | mail | (none) | WebRTC health check |
| `discuss_thread_admin` | all ons_discuss_* | (none) | Meta-package |

### Tier 2 — Core Platform (Phase 4.1–4.3)

| Module | Depends | Key Models | Purpose |
|--------|---------|------------|---------|
| `ons_ops_core` | base, mail, contacts | ons.interaction, ons.call.driver, res.partner (ext) | Shared models, utilities, partner extensions |
| `ons_ops_intake` | ons_ops_core | ons.interaction (ext) | Call intake form, AI classification, 3CX trigger |
| `ons_ops_crm` | crm, ons_ops_core | crm.lead (ext) | Lead scoring, nurture tracking, conversion attribution |

### Tier 3 — Service Operations (Phase 4.4–4.7)

| Module | Depends | Key Models | Purpose |
|--------|---------|------------|---------|
| `ons_ops_cases` | ons_ops_core | ons.case, ons.case.stage, ons.session | Case management, session pipeline |
| `ons_ops_dispatch` | ons_ops_cases | ons.dispatch | On-site dispatch, WorkMarket integration, voice callbacks |
| `ons_ops_3cx` | ons_ops_core | ons.threecx.queue, ons.threecx.agent | 3CX sync, realtime call monitoring, queue stats |
| `ons_ops_ai` | ons_ops_core | ons.qa.evaluation, ons.qa.rule | AI grading, transcription, summarization, coaching |

### Tier 4 — Communication & Reporting (Phase 4.8–4.10)

| Module | Depends | Key Models | Purpose |
|--------|---------|------------|---------|
| `ons_ops_comms` | mail, ons_ops_core | ons.sms.thread, ons.reminder | Email/SMS/voice reminders, shared inbox |
| `ons_ops_reports` | ons_ops_core, ons_ops_cases | (views only) | Dashboards, KPIs, performance analytics |
| `ons_ops_shell` | web, ons_ops_core | (JS/XML only) | Left-nav cockpit, custom home, menu cleanup |

### Tier 5 — Financial & Portal (Phase 4.11–4.12)

| Module | Depends | Key Models | Purpose |
|--------|---------|------------|---------|
| `ons_ops_billing` | account, ons_ops_cases | account.move (ext) | Stripe/Zoho sync, payment matching, auto-invoice |
| `ons_ops_portal` | portal, ons_ops_core | (templates) | Customer-facing portal for case status, payments |

---

## Circular Dependency Prevention

Rules:
1. `ons_ops_core` NEVER depends on any `ons_ops_*` module
2. Sibling modules (crm, intake, cases) communicate via `ons_ops_core` models
3. Cross-module references use `ir.actions.act_window` not Python imports
4. Daemon services (3CX realtime, voice TTS) stay external if sub-second latency needed

---

## OCA Modules Under Evaluation

| OCA Repo | Module | Status | Decision |
|----------|--------|--------|----------|
| oca-helpdesk | helpdesk_mgmt | Evaluated | **Skip** — our case model is more specific |
| oca-field-service | fieldservice | Evaluated | **Maybe** — evaluate if dispatch needs mapping |
| oca-contract | contract | Evaluated | **Later** — for subscription management in Tier 5 |
| oca-dms | dms | Evaluated | **Later** — for document management if needed |
| oca-knowledge | knowledge | Evaluated | **Skip** — not needed for MVP |
