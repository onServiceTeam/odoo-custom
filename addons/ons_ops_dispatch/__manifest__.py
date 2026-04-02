# -*- coding: utf-8 -*-
{
    "name": "ONS Operations — Dispatch",
    "version": "19.0.1.0.0",
    "category": "Services",
    "summary": "Onsite dispatch orchestration, applicants, reminders, checklists, and voice outcomes",
    "author": "onService",
    "license": "LGPL-3",
    "depends": [
        "ons_ops_cases",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/dispatch_sequence.xml",
        "data/dispatch_status_data.xml",
        "data/checklist_config_data.xml",
        "data/cancellation_reason_data.xml",
        "views/dispatch_views.xml",
        "views/applicant_views.xml",
        "views/checklist_views.xml",
        "views/reminder_views.xml",
        "views/voice_call_views.xml",
        "views/case_views.xml",
        "views/ops_dispatch_menus.xml",
    ],
    "installable": True,
    "application": False,
}
