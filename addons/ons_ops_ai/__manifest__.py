{
    'name': 'onService Operations — AI Services',
    'version': '19.0.1.0.0',
    'category': 'Operations',
    'summary': 'AI provider config, task routing, prompt contracts, run audit logging',
    'description': """
        Central AI service layer for onService Operations.
        Owns provider/model configuration, task→model routing,
        prompt template contracts, run audit logs, and budget enforcement.
        Actual AI API calls remain in the Node.js sidecar.
    """,
    'author': 'onService',
    'website': 'https://onservice.us',
    'license': 'LGPL-3',
    'depends': [
        'ons_ops_cases',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/provider_data.xml',
        'data/prompt_template_data.xml',
        'views/provider_views.xml',
        'views/model_views.xml',
        'views/task_views.xml',
        'views/prompt_template_views.xml',
        'views/run_views.xml',
        'views/budget_views.xml',
        'views/interaction_views.xml',
        'views/case_views.xml',
        'views/ops_ai_menus.xml',
    ],
    'installable': True,
    'application': False,
}
