# -*- coding: utf-8 -*-
{
    "name": "OnService Discuss UI",
    "version": "19.0.1.0.0",
    "category": "Discuss",
    "summary": "Discord/Slack theme, work status, tab counter, category config, IM status lockdown",
    "description": """
OnService Discuss UI
====================

Discord/Slack-inspired visual overhaul and UX enhancements for Odoo 19 Discuss:

* Discord/Slack hybrid theme (light + dark mode)
* Slack-style work status presets (In a meeting, Working remotely, etc.)
* Unread count in browser tab title
* Configurable sidebar category labels
* Hide "Looking for Help" category
* Real presence only — no fake IM status
* Admin-only thread deletion toggle
* Auto-cleanup of empty group channels
    """,
    "author": "OnService",
    "website": "https://team.onservice.us",
    "license": "LGPL-3",
    "depends": ["mail"],
    "data": [
        "views/res_config_settings_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "ons_discuss_ui/static/src/scss/discord_theme.scss",
            "ons_discuss_ui/static/src/xml/work_status_dropdown.xml",
            "ons_discuss_ui/static/src/js/store_service_patch.js",
            "ons_discuss_ui/static/src/js/discuss_ux_patch.js",
            "ons_discuss_ui/static/src/js/work_status_dropdown.js",
            "ons_discuss_ui/static/src/js/category_config_patch.js",
        ],
        "web.assets_web_dark": [
            "ons_discuss_ui/static/src/scss/discord_theme.dark.scss",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
}
