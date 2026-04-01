# -*- coding: utf-8 -*-
{
    "name": "OnService Discuss Threads",
    "version": "19.0.1.0.0",
    "category": "Discuss",
    "summary": "Thread admin, kick/delete/hard-delete, drag-and-drop reorder, customer intake",
    "description": """
OnService Discuss Threads
=========================

Admin controls for thread and channel management in Odoo 19 Discuss:

* Admin-only thread deletion toggle
* Admin hard-delete messages (permanent removal)
* Admin kick/remove any member from any channel
* Admin drag-and-drop channel reordering
* Last-member leave warning with auto-cleanup
* Customer intake model with auto-thread creation
* Backend admin views for channels, members, and intakes
    """,
    "author": "OnService",
    "website": "https://team.onservice.us",
    "license": "LGPL-3",
    "depends": ["mail", "ons_discuss_ui"],
    "data": [
        "security/ir.model.access.csv",
        "views/admin_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "ons_discuss_threads/static/src/xml/sidebar_reorder.xml",
            "ons_discuss_threads/static/src/js/store_service_patch.js",
            "ons_discuss_threads/static/src/js/thread_actions_patch.js",
            "ons_discuss_threads/static/src/js/delete_thread_dialog_patch.js",
            "ons_discuss_threads/static/src/js/message_actions_patch.js",
            "ons_discuss_threads/static/src/js/channel_actions_patch.js",
            "ons_discuss_threads/static/src/js/leave_channel_patch.js",
            "ons_discuss_threads/static/src/js/sidebar_reorder_patch.js",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
}
