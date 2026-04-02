from odoo import api, fields, models


class OnsCase(models.Model):
    _inherit = 'ons.case'

    ai_run_ids = fields.One2many(
        'ons.ai.run', 'res_id',
        string='AI Runs',
        domain=lambda self: [('res_model', '=', 'ons.case')],
    )
    ai_run_count = fields.Integer(compute='_compute_ai_run_count')
    ai_summary = fields.Text(
        string='AI Summary',
        help='AI-generated case summary. Advisory — agent should review.',
    )
    customer_report = fields.Text(
        string='Customer Report',
        help='Sanitized customer-facing service report.',
    )

    @api.depends('ai_run_ids')
    def _compute_ai_run_count(self):
        for rec in self:
            rec.ai_run_count = self.env['ons.ai.run'].search_count([
                ('res_model', '=', 'ons.case'),
                ('res_id', '=', rec.id),
            ])

    def action_view_ai_runs(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'AI Runs',
            'res_model': 'ons.ai.run',
            'view_mode': 'list,form',
            'domain': [
                ('res_model', '=', 'ons.case'),
                ('res_id', '=', self.id),
            ],
        }

    def action_ai_summarize(self):
        """Request AI case summary generation."""
        self.ensure_one()
        self.env['ons.ai.budget'].check_budget()
        task = self.env['ons.ai.task'].get_task_config('ticket_summary')

        prompt_result = self.env['ons.ai.prompt.template'].render(
            'ticket_summary',
            {
                'case_description': self.issue_description or '',
                'case_notes': self.summary or '',
                'interaction_history': '',
            },
        )

        self.env['ons.ai.run'].log_run({
            'task_type': 'ticket_summary',
            'requested_model': task.get('model_id', ''),
            'res_model': 'ons.case',
            'res_id': self.id,
            'success': False,
            'prompt_template_id': prompt_result.get('template_id'),
            'prompt_version': prompt_result.get('version', 0),
            'request_summary': (self.issue_description or '')[:500],
        })

    def action_ai_customer_report(self):
        """Request AI customer report generation."""
        self.ensure_one()
        self.env['ons.ai.budget'].check_budget()
        task = self.env['ons.ai.task'].get_task_config('customer_report')

        prompt_result = self.env['ons.ai.prompt.template'].render(
            'customer_report',
            {
                'case_description': self.issue_description or '',
                'actions_taken': self.summary or '',
                'resolution': '',
            },
        )

        self.env['ons.ai.run'].log_run({
            'task_type': 'customer_report',
            'requested_model': task.get('model_id', ''),
            'res_model': 'ons.case',
            'res_id': self.id,
            'success': False,
            'prompt_template_id': prompt_result.get('template_id'),
            'prompt_version': prompt_result.get('version', 0),
            'request_summary': (self.issue_description or '')[:500],
        })
