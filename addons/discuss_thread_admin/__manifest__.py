# -*- coding: utf-8 -*-
{
    "name": "Discuss Administration Suite",
    "version": "19.0.5.2.0",
    "category": "Discuss",
    "summary": "Admin controls: thread/channel management, message moderation, member oversight, auto-cleanup",
    "description": """
Discuss Administration Suite
============================

Comprehensive admin controls for Odoo 19 Discuss:

* Admin-only thread deletion toggle
* Auto-cleanup of empty group channels when all members leave
* Last-member leave warning
* Backend admin views for channels and members
* Admin can kick/remove any member from any channel
* Admin hard-delete messages (permanent removal)
* Discord/Slack-inspired visual theme with visible thread connectors
* Real presence only — no fake status (online/offline based on activity)
* Slack-style work status presets (In a meeting, Working remotely, etc.)
* Discord-style persistent voice channels with auto-join
* Admin drag-and-drop channel reordering
* GIPHY integration for GIF picker (replaces discontinued Tenor)
    """,
    "author": "OnService",
    "website": "https://team.onservice.us",
    "license": "LGPL-3",
    "depends": ["mail"],
    "data": [
        "security/ir.model.access.csv",
        "views/res_config_settings_views.xml",
        "views/admin_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "discuss_thread_admin/static/src/scss/discord_theme.scss",
            "discuss_thread_admin/static/src/xml/work_status_dropdown.xml",
            "discuss_thread_admin/static/src/xml/voice_channel_sidebar.xml",
            "discuss_thread_admin/static/src/xml/sidebar_reorder.xml",
            "discuss_thread_admin/static/src/js/store_service_patch.js",
            "discuss_thread_admin/static/src/js/thread_actions_patch.js",
            "discuss_thread_admin/static/src/js/delete_thread_dialog_patch.js",
            "discuss_thread_admin/static/src/js/message_actions_patch.js",
            "discuss_thread_admin/static/src/js/channel_actions_patch.js",
            "discuss_thread_admin/static/src/js/leave_channel_patch.js",
            "discuss_thread_admin/static/src/js/discuss_ux_patch.js",
            "discuss_thread_admin/static/src/js/work_status_dropdown.js",
            "discuss_thread_admin/static/src/js/voice_channel_patch.js",
            "discuss_thread_admin/static/src/js/sidebar_reorder_patch.js",
            "discuss_thread_admin/static/src/js/category_config_patch.js",
            "discuss_thread_admin/static/src/js/gif_composer_patch.js",
        ],
        "web.assets_web_dark": [
            "discuss_thread_admin/static/src/scss/discord_theme.dark.scss",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
}
