{
    "name": "onService Operations — QA Engine",
    "version": "19.0.1.0.0",
    "category": "Operations/QA",
    "summary": "Operational QA evaluations, reviews, acknowledgements, and coaching",
    "description": """
        QA engine for call quality evaluation.
        - QA result lifecycle (grade → review → acknowledge)
        - Rule/rubric definitions and call type configuration
        - Per-finding evidence and scoring
        - Coaching artifacts with AI generation hooks
        - Agent acknowledgement and dispute flow
    """,
    "author": "onService",
    "website": "https://onservice.us",
    "license": "LGPL-3",
    "depends": [
        "ons_ops_3cx",
        "ons_ops_ai",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/call_type_data.xml",
        "data/rule_data.xml",
        "views/result_views.xml",
        "views/finding_views.xml",
        "views/coaching_views.xml",
        "views/rule_views.xml",
        "views/call_type_views.xml",
        "views/call_log_views.xml",
        "views/ops_qa_menus.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
