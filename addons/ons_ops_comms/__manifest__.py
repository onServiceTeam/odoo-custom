# -*- coding: utf-8 -*-
{
    "name": "ONS Operations — Communications",
    "version": "19.0.1.0.0",
    "category": "Services",
    "summary": "SMS/email thread logging, notification rules, message templates, and communication hub",
    "author": "onService",
    "license": "LGPL-3",
    "depends": [
        "ons_ops_cases",
        "ons_ops_dispatch",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/event_type_data.xml",
        "views/sms_views.xml",
        "views/email_views.xml",
        "views/notification_rule_views.xml",
        "views/notification_log_views.xml",
        "views/message_template_views.xml",
        "views/case_views.xml",
        "views/dispatch_views.xml",
        "views/ops_comms_menus.xml",
    ],
    "installable": True,
    "application": False,
}
