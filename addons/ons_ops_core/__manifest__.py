# -*- coding: utf-8 -*-
{
    "name": "onService Operations — Core",
    "version": "19.0.1.0.0",
    "category": "Services",
    "summary": "Security groups and foundation for onService operations modules",
    "description": """
onService Operations Core
=========================

Foundation module for the onService Operations Center.

* **Security groups**: Agent / Manager / Administrator hierarchy
* **Module category**: onService Operations (appears on user form)
* **Config namespace**: reserved ``ons_ops_core.*`` parameters

This module has no UI of its own. It provides the security
infrastructure that all ``ons_ops_*`` modules depend on.

Upgrade Safety
--------------
* Groups use a dedicated ``ir.module.category`` — no conflict with
  stock Odoo, Enterprise, or OCA groups.
* No stock models are modified.
* No views are inherited or altered.
    """,
    "author": "OnService",
    "website": "https://team.onservice.us",
    "license": "LGPL-3",
    "depends": ["base"],
    "data": [
        "security/ons_ops_security.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
