# -*- coding: utf-8 -*-
{
    "name": "Discuss Administration Suite",
    "version": "19.0.6.0.0",
    "category": "Discuss",
    "summary": "Meta-package: installs all OnService Discuss addons",
    "description": """
Discuss Administration Suite — Meta-package
=============================================

This module has been refactored into separate ons_* addons:

* **ons_discuss_ui** — Discord/Slack theme, work status, tab counter, category config
* **ons_gif_provider** — GIPHY integration for GIF picker
* **ons_discuss_threads** — Thread admin, kick/delete/hard-delete, reorder, intake
* **ons_discuss_voice** — Persistent voice channels with auto-join
* **ons_webrtc** — TURN/STUN/SFU configuration management

Installing this module installs all of the above.
    """,
    "author": "OnService",
    "website": "https://team.onservice.us",
    "license": "LGPL-3",
    "depends": [
        "ons_discuss_ui",
        "ons_gif_provider",
        "ons_discuss_threads",
        "ons_discuss_voice",
        "ons_webrtc",
    ],
    "data": [],
    "assets": {},
    "installable": True,
    "application": False,
    "auto_install": False,
}
