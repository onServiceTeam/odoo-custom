# -*- coding: utf-8 -*-
{
    "name": "onService Operations — 3CX Telephony",
    "version": "19.0.1.0.0",
    "category": "Services",
    "summary": "3CX call logs, active calls, agent status, extension mapping, and screen-pop data",
    "description": """
onService Operations — 3CX Telephony
======================================

Telephony integration layer for the onService Operations Center.

* **ons.call.log** — Permanent CDR records normalised from 3CX XAPI
  recordings endpoint.  Includes caller/callee numbers, queue attribution,
  agent extension, duration breakdowns, disposition, recording URL, and
  partner resolution with ambiguity detection.
* **ons.active.call** — Ephemeral active-call records refreshed from the
  3CX XAPI ``/activecalls`` endpoint.  Records older than 1 hour are
  auto-purged each sync cycle.
* **ons.agent.status** — Current agent presence (Available, OnCall, DND,
  Away, Offline, …) mapped through extension→user lookup.
* **ons.user.extension** — Admin-managed 3CX extension ↔ ``res.users``
  mapping with unique constraint.
* **ons.interaction extension** — Adds ``call_log_id`` link from
  interaction to the underlying CDR record.
* **Cron jobs** — Periodic CDR sync (15 min), active-call refresh
  (1 min), and recording cleanup.
* **Server action** — "Create Interaction" from call log with
  pre-populated telephony context.

Upgrade Safety
--------------
* All custom models use ``ons.*`` namespace.
* ``ons.interaction`` extension adds fields only.
* No 3CX-specific logic in stock models.
* 3CX API credentials stored in ``ir.config_parameter``.
* Sub-10s realtime polling deferred to a future sidecar daemon;
  MVP uses Odoo cron with 1-minute interval.
    """,
    "author": "OnService",
    "website": "https://team.onservice.us",
    "license": "LGPL-3",
    "depends": [
        "ons_ops_cases",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/cron_data.xml",
        "views/call_log_views.xml",
        "views/active_call_views.xml",
        "views/agent_status_views.xml",
        "views/user_extension_views.xml",
        "views/interaction_views.xml",
        "views/ops_3cx_menus.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
