# -*- coding: utf-8 -*-
{
    "name": "OnService GIF Provider (GIPHY)",
    "version": "19.0.1.0.0",
    "category": "Discuss",
    "summary": "GIPHY integration for Discuss GIF picker (replaces discontinued Tenor)",
    "description": """
OnService GIF Provider — GIPHY
===============================

Replaces the discontinued Google Tenor API (January 2026) with GIPHY
as the GIF provider for Odoo 19 Discuss:

* Overrides stock /discuss/gif/* endpoints with GIPHY equivalents
* GIF picker renders inline images (not links)
* GIPHY API key managed via Settings > Discuss
* Hides the stock Tenor API key setting
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
            "ons_gif_provider/static/src/js/gif_composer_patch.js",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
}
