# -*- coding: utf-8 -*-
{
    "name": "OnService Discuss Voice",
    "version": "19.0.1.0.0",
    "category": "Discuss",
    "summary": "Discord-style persistent voice channels with auto-join/leave",
    "description": """
OnService Discuss Voice
=======================

Discord-style persistent voice channels for Odoo 19 Discuss:

* Voice channel flag on discuss.channel
* Auto-join voice call when entering a voice channel
* Auto-leave voice call when navigating away
* Suppress "started a call" notifications for voice channels
* Speaker icon in sidebar for voice channels
* Admin toggle to mark channels as voice channels
    """,
    "author": "OnService",
    "website": "https://team.onservice.us",
    "license": "LGPL-3",
    "depends": ["mail", "ons_discuss_threads"],
    "data": [
        "views/admin_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "ons_discuss_voice/static/src/xml/voice_channel_sidebar.xml",
            "ons_discuss_voice/static/src/js/store_service_patch.js",
            "ons_discuss_voice/static/src/js/voice_channel_patch.js",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
}
