# -*- coding: utf-8 -*-
{
    "name": "onService Operations — Intake",
    "version": "19.0.1.0.0",
    "category": "Services",
    "summary": "Call intake, interaction tracking, and call-driver classification",
    "description": """
onService Operations — Intake
==============================

Core intake module for the onService Operations Center.

* **ons.call.driver** — Catalog of call-reason codes with categories
* **ons.interaction** — Atomic contact record (phone / email / sms / web)
* Intake form with auto phone-dedup and customer resolution
* Hooks for AI classification (primary / secondary driver codes)
* Links interactions to ``crm.lead`` or downstream ``ons.case``

Upgrade Safety
--------------
* Extends ``res.partner`` with three new fields (no stock field changes).
* Extends ``crm.lead`` with an ``interaction_id`` link.
* No stock views are replaced — only inherited with xpath.
    """,
    "author": "OnService",
    "website": "https://team.onservice.us",
    "license": "LGPL-3",
    "depends": [
        "ons_ops_core",
        "contacts",
        "crm",
        "phone_validation",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/ons_call_driver_data.xml",
        "views/interaction_views.xml",
        "views/call_driver_views.xml",
        "views/partner_views.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
