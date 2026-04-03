# -*- coding: utf-8 -*-
{
    "name": "onService Operations — Web Theme",
    "version": "19.0.1.0.0",
    "category": "Services/Theme",
    "summary": "Custom UI theme matching the legacy onService dashboard design",
    "author": "OnService",
    "website": "https://team.onservice.us",
    "license": "LGPL-3",
    "depends": [
        "web",
        "ons_ops_intake",
        "ons_ops_cases",
    ],
    "data": [
        "views/webclient_templates.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "ons_ops_web/static/src/scss/variables.scss",
            "ons_ops_web/static/src/scss/layout.scss",
            "ons_ops_web/static/src/scss/forms.scss",
            "ons_ops_web/static/src/scss/intake_form.scss",
            "ons_ops_web/static/src/scss/session_tracker.scss",
            "ons_ops_web/static/src/scss/badges.scss",
            "ons_ops_web/static/src/scss/buttons.scss",
            "ons_ops_web/static/src/scss/kanban.scss",
            "ons_ops_web/static/src/js/intake_form.js",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
}
