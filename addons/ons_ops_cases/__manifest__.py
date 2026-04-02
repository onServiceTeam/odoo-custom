# -*- coding: utf-8 -*-
{
    "name": "onService Operations — Cases",
    "version": "19.0.1.0.0",
    "category": "Services",
    "summary": "Case lifecycle, pipeline stages, session tracker, and stage history",
    "description": """
onService Operations — Cases
=============================

Custom case management for the onService Operations Center.

* **ons.case** — Service case with 12-stage pipeline matching legacy
  session tracker.  Three role-based assignments (intake, tech, billing).
  Aging buckets, stale flags, and needs-attention indicators.
* **ons.case.stage** — Ordered pipeline stages with kanban support.
  Seed data matches the 12 canonical legacy stages exactly.
* **ons.case.stage.history** — Audit log of every stage transition
  with duration tracking and override flag.
* **crm.lead extension** — ``case_id`` link and ``Convert to Case``
  action for qualified leads.
* **ons.interaction extension** — ``case_id`` back-link.
* **Session Tracker** — List and kanban views reproducing the legacy
  session tracker with filters for aging, assignment, and stage.

Upgrade Safety
--------------
* Custom models only — no stock model schema changes.
* crm.lead extension adds one Many2one field and one button.
* ons.interaction extension adds one Many2one field.
    """,
    "author": "OnService",
    "website": "https://team.onservice.us",
    "license": "LGPL-3",
    "depends": [
        "ons_ops_crm",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/ir_sequence_data.xml",
        "data/case_stage_data.xml",
        "views/case_stage_views.xml",
        "views/case_views.xml",
        "views/ops_cases_menus.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
