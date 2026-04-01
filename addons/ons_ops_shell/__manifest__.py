# -*- coding: utf-8 -*-
{
    "name": "onService Operations — Shell",
    "version": "19.0.1.0.0",
    "category": "Services",
    "summary": "Operations center navigation, dashboard, and menu framework",
    "description": """
onService Operations Shell
==========================

The main entry point for the onService Operations Center.

Provides:

* **Top-level "Operations" application menu** visible to all agents
* **Home dashboard** with live KPI cards and quick-action buttons
* **Section menus** (Intake & CRM, Communication, Management, Configuration)
  that future ``ons_ops_*`` modules populate with their own items
* **Role-based visibility** via ``ons_ops_core`` security groups

Menu Architecture
-----------------
::

    Operations (app root → dashboard)
    ├── Dashboard
    ├── Intake & CRM
    │   ├── Customers          → res.partner (Contacts)
    │   └── Pipeline           → crm.lead (CRM Pipeline)
    ├── Communication
    │   └── Discuss            → Odoo Discuss
    ├── Management             → (manager+ only, populated by future modules)
    └── Configuration          → (admin only, populated by future modules)

Future modules add their leaf menus under the appropriate section parent.

Upgrade Safety
--------------
* Uses standard ``ir.ui.menu`` records — stable across Odoo versions.
* Dashboard is a client action with an Owl component — monitor ``@web``
  imports on major upgrades.
* No stock menus are hidden or removed — only additive changes.
* No stock models are modified.
    """,
    "author": "OnService",
    "website": "https://team.onservice.us",
    "license": "LGPL-3",
    "depends": [
        "ons_ops_core",
        "contacts",
        "crm",
        "mail",
    ],
    "data": [
        "views/ops_dashboard_action.xml",
        "views/ops_menus.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "ons_ops_shell/static/src/scss/ops_dashboard.scss",
            "ons_ops_shell/static/src/xml/ops_dashboard.xml",
            "ons_ops_shell/static/src/js/ops_dashboard.js",
        ],
    },
    "installable": True,
    "application": True,
    "auto_install": False,
}
