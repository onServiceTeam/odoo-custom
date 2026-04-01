# -*- coding: utf-8 -*-
{
    "name": "OnService WebRTC Config",
    "version": "19.0.1.0.0",
    "category": "Discuss",
    "summary": "TURN/STUN/SFU configuration management and health check",
    "description": """
OnService WebRTC Config
=======================

Configuration management addon for WebRTC infrastructure:

* Health-check endpoint for TURN/STUN/SFU services
* Documents the external infrastructure:
  - coturn TURN server (port 3478)
  - Odoo SFU server (port 8070)
  - ICE server configuration in mail_ice_server table

No custom models — configuration lives in ir.config_parameter
and mail.ice.server records managed via Odoo Settings.
    """,
    "author": "OnService",
    "website": "https://team.onservice.us",
    "license": "LGPL-3",
    "depends": ["mail"],
    "data": [],
    "installable": True,
    "application": False,
    "auto_install": False,
}
