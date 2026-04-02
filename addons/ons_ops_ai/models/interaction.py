import re

from odoo import api, fields, models


# Words that must never appear in customer-facing AI output
_CUSTOMER_BLOCKED_WORDS = {
    'ai', 'summary', 'automated', 'generated', 'bot',
    'trust', 'trusting', 'trusted',
    'scammer', 'runner', 'cheap', 'rude',
    'upsell', 'downsell', 'discount', 'comp',
    'commission', 'profit', 'margin',
    'discord', '@',
}

_PRICING_PATTERN = re.compile(r'\$\d+')


class OnsInteraction(models.Model):
    _inherit = 'ons.interaction'

    ai_run_ids = fields.One2many(
        'ons.ai.run', 'res_id',
        string='AI Runs',
        domain=lambda self: [('res_model', '=', 'ons.interaction')],
    )
    ai_run_count = fields.Integer(compute='_compute_ai_run_count')

    @api.depends('ai_run_ids')
    def _compute_ai_run_count(self):
        for rec in self:
            rec.ai_run_count = self.env['ons.ai.run'].search_count([
                ('res_model', '=', 'ons.interaction'),
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
                ('res_model', '=', 'ons.interaction'),
                ('res_id', '=', self.id),
            ],
        }

    def action_ai_classify(self):
        """Request AI classification for this interaction.

        Creates a queued run log entry for the sidecar to pick up and process.
        The sidecar will call the AI API and write back driver/confidence fields.
        """
        self.ensure_one()
        self.env['ons.ai.budget'].check_budget()
        task = self.env['ons.ai.task'].get_task_config('intake_classification')

        # Build driver context for the prompt
        drivers = self.env['ons.call.driver'].search([('active', '=', True)])
        driver_list = '\n'.join(
            f"- {d.code}: {d.name} (keywords: {d.detection_keywords or ''})"
            for d in drivers
        )

        prompt_result = self.env['ons.ai.prompt.template'].render(
            'intake_classify',
            {
                'driver_list': driver_list,
                'description': self.issue_description or '',
                'transcript': self.transcript or '',
            },
        )

        # Create a queued run entry — sidecar picks this up
        self.env['ons.ai.run'].log_run({
            'task_type': 'intake_classification',
            'requested_model': task.get('model_id', ''),
            'res_model': 'ons.interaction',
            'res_id': self.id,
            'success': False,  # pending — sidecar updates on completion
            'prompt_template_id': prompt_result.get('template_id'),
            'prompt_version': prompt_result.get('version', 0),
            'request_summary': (self.issue_description or '')[:500],
        })

    def action_ai_polish(self):
        """Request AI description polish for this interaction."""
        self.ensure_one()
        self.env['ons.ai.budget'].check_budget()
        task = self.env['ons.ai.task'].get_task_config('description_polish')

        prompt_result = self.env['ons.ai.prompt.template'].render(
            'description_polish',
            {'description': self.issue_description or ''},
        )

        self.env['ons.ai.run'].log_run({
            'task_type': 'description_polish',
            'requested_model': task.get('model_id', ''),
            'res_model': 'ons.interaction',
            'res_id': self.id,
            'success': False,
            'prompt_template_id': prompt_result.get('template_id'),
            'prompt_version': prompt_result.get('version', 0),
            'request_summary': (self.issue_description or '')[:500],
        })

    @staticmethod
    def sanitize_for_customer(text):
        """Remove internal jargon and blocked words from customer-facing text.

        Mirrors legacy sanitizeForCustomer() function.
        """
        if not text:
            return ''
        result = text
        # Remove pricing patterns
        result = _PRICING_PATTERN.sub('', result)
        # Remove blocked words (case-insensitive, whole word)
        for word in _CUSTOMER_BLOCKED_WORDS:
            result = re.sub(
                rf'\b{re.escape(word)}\b', '', result, flags=re.IGNORECASE,
            )
        # Clean up extra whitespace
        result = re.sub(r'\s+', ' ', result).strip()
        return result
