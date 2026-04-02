# -*- coding: utf-8 -*-
{
    "name": "onService — Customer Portal",
    "version": "19.0.1.0.0",
    "category": "Services/Portal",
    "summary": "Customer self-service: cases, plans, dispatches, consent",
    "description": "Extends /my portal with service cases, subscription plans, "
                   "onsite dispatches, and consent preference management.",
    "author": "onService",
    "depends": [
        "portal",
        "website",
        "ons_ops_cases",
        "ons_ops_billing",
        "ons_ops_dispatch",
        "ons_ops_comms",
        "ons_ops_crm",
        "ons_ops_ai",
    ],
    "data": [
        "security/ir.model.access.csv",
        "security/portal_rules.xml",
        "views/portal_templates.xml",
        "views/portal_case.xml",
        "views/portal_plan.xml",
        "views/portal_dispatch.xml",
        "views/portal_consent.xml",
    ],
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3",
}
