# -*- coding: utf-8 -*-
{
    "name": "onService Operations — Reports",
    "version": "19.0.1.0.0",
    "category": "Operations/Reports",
    "summary": "Operational reporting: agent, queue, and driver daily KPIs",
    "author": "onService",
    "license": "LGPL-3",
    "depends": [
        "ons_ops_3cx",
        "ons_ops_cases",
        "ons_ops_billing",
        "ons_ops_dispatch",
        "ons_ops_qa",
        "ons_ops_ai",
    ],
    "data": [
        "security/ir.model.access.csv",
        "security/report_rules.xml",
        "data/cron_data.xml",
        "views/agent_daily_views.xml",
        "views/queue_daily_views.xml",
        "views/driver_daily_views.xml",
        "views/ops_reports_menus.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
