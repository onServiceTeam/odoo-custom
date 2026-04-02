# -*- coding: utf-8 -*-
{
    "name": "onService Operations — CRM",
    "version": "19.0.1.0.0",
    "category": "Services",
    "summary": "CRM lead lifecycle, consent tracking, and interaction-to-lead conversion",
    "description": """
onService Operations — CRM
===========================

CRM and consent layer for the onService Operations Center.

* **crm.lead extensions** — Lead type, caller relationship, callback
  tracking, decline path, nurture eligibility, duplicate prevention
* **ons.contact.consent** — Per-channel, per-scope opt-in/opt-out
  tracking with full audit trail
* **Interaction → Lead** — Business actions to create leads from
  classified interactions with auto-population
* **Custom lost reasons** — Business-specific reasons replacing stock

Upgrade Safety
--------------
* Extends ``crm.lead`` with new fields only (no stock field changes).
* Uses stock CRM stages (New / Qualified / Proposition / Won).
* New ``ons.contact.consent`` model — no stock model conflicts.
* Consent records are NEVER deleted — only archived.
    """,
    "author": "OnService",
    "website": "https://team.onservice.us",
    "license": "LGPL-3",
    "depends": [
        "ons_ops_intake",
        "crm",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/crm_lost_reason_data.xml",
        "views/crm_lead_views.xml",
        "views/consent_views.xml",
        "views/partner_views.xml",
        "views/ops_crm_menus.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
