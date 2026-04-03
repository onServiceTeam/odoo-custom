import json
import logging
import re

from odoo import api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

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

    def _get_ai_provider(self):
        """Get the active OpenAI chat provider."""
        provider = self.env['ons.ai.provider'].sudo().search([
            ('name', '=', 'openai'),
            ('is_active', '=', True),
            ('provider_type', '=', 'chat'),
        ], limit=1)
        if not provider:
            raise UserError("No active OpenAI provider configured. Go to Operations → Configuration → AI Providers.")
        if not provider.api_key:
            raise UserError("OpenAI API key not set. Go to Operations → Configuration → AI Providers → OpenAI.")
        return provider

    def action_ai_classify(self):
        """Call OpenAI to classify this interaction's issue into call drivers."""
        self.ensure_one()
        self.env['ons.ai.budget'].check_budget()
        task = self.env['ons.ai.task'].get_task_config('intake_classification')
        provider = self._get_ai_provider()

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

        try:
            result = provider._call_api(
                model_id=task['model_id'],
                system_prompt=prompt_result['system_prompt'],
                user_prompt=prompt_result['user_prompt'],
                max_tokens=task.get('max_tokens', 4000),
                temperature=task.get('temperature', 0.3),
            )

            # Parse JSON response
            content = result['content'].strip()
            # Strip markdown code fences if present
            if content.startswith('```'):
                content = re.sub(r'^```(?:json)?\n?', '', content)
                content = re.sub(r'\n?```$', '', content)

            parsed = json.loads(content)

            # Apply classification results
            primary = parsed.get('primary_driver', {})
            if primary.get('code'):
                driver = self.env['ons.call.driver'].search([
                    ('code', '=', primary['code']),
                ], limit=1)
                if driver:
                    self.primary_driver_id = driver
                    self.ai_confidence = primary.get('confidence', 0.0)

            # Secondary drivers
            secondary_codes = [d.get('code') for d in parsed.get('secondary_drivers', []) if d.get('code')]
            if secondary_codes:
                sec_drivers = self.env['ons.call.driver'].search([('code', 'in', secondary_codes)])
                if sec_drivers:
                    self.secondary_driver_ids = [(6, 0, sec_drivers.ids)]

            # Urgency
            if parsed.get('urgency') in ('low', 'medium', 'high', 'urgent'):
                self.urgency = parsed['urgency']

            self.ai_classification_raw = content
            if self.state == 'new':
                self.state = 'classified'

            # Log successful run
            self._log_ai_run(task, prompt_result, result, success=True)

        except (json.JSONDecodeError, KeyError) as e:
            _logger.warning("AI classify parse error for interaction %s: %s", self.name, e)
            self._log_ai_run(task, prompt_result, result, success=False, error=str(e))
            raise UserError("AI returned invalid response. The raw output has been logged.")
        except UserError:
            raise
        except Exception as e:
            _logger.exception("AI classify error for interaction %s", self.name)
            raise UserError("AI classification failed: %s" % str(e))

    def action_ai_polish(self):
        """Call OpenAI to polish the issue description text."""
        self.ensure_one()
        if not self.issue_description:
            raise UserError("Enter an issue description first.")
        self.env['ons.ai.budget'].check_budget()
        task = self.env['ons.ai.task'].get_task_config('description_polish')
        provider = self._get_ai_provider()

        prompt_result = self.env['ons.ai.prompt.template'].render(
            'description_polish',
            {'description': self.issue_description or ''},
        )

        try:
            result = provider._call_api(
                model_id=task['model_id'],
                system_prompt=prompt_result['system_prompt'],
                user_prompt=prompt_result['user_prompt'],
                max_tokens=task.get('max_tokens', 4000),
                temperature=task.get('temperature', 0.3),
            )

            polished = result['content'].strip()
            # Strip markdown code fences if present
            if polished.startswith('```'):
                polished = re.sub(r'^```(?:\w+)?\n?', '', polished)
                polished = re.sub(r'\n?```$', '', polished)

            self.issue_description = polished
            self._log_ai_run(task, prompt_result, result, success=True)

        except UserError:
            raise
        except Exception as e:
            _logger.exception("AI polish error for interaction %s", self.name)
            raise UserError("AI polish failed: %s" % str(e))

    def _log_ai_run(self, task_config, prompt_result, api_result, success=True, error=None):
        """Log an AI run to the audit trail."""
        model_rec = self.env['ons.ai.model'].search([
            ('model_id', '=', api_result.get('model_used', task_config.get('model_id', ''))),
        ], limit=1)

        # Compute cost
        input_tokens = api_result.get('input_tokens', 0)
        output_tokens = api_result.get('output_tokens', 0)
        total_cost = 0.0
        if model_rec:
            total_cost = (
                (input_tokens / 1000.0) * (model_rec.input_cost_per_1k or 0)
                + (output_tokens / 1000.0) * (model_rec.output_cost_per_1k or 0)
            )

        self.env['ons.ai.run'].log_run({
            'task_type': task_config.get('task_type', ''),
            'model_id': model_rec.id if model_rec else False,
            'requested_model': task_config.get('model_id', ''),
            'actual_model': api_result.get('model_used', ''),
            'input_tokens': input_tokens,
            'output_tokens': output_tokens,
            'total_cost': total_cost,
            'duration_ms': api_result.get('duration_ms', 0),
            'success': success,
            'error_message': error or '',
            'res_model': 'ons.interaction',
            'res_id': self.id,
            'prompt_template_id': prompt_result.get('template_id'),
            'prompt_version': prompt_result.get('version', 0),
            'request_summary': (self.issue_description or '')[:500],
            'response_summary': (api_result.get('content', ''))[:500],
        })

    def _hook_after_intake(self):
        """Auto-trigger AI classification after intake submission (if configured)."""
        super()._hook_after_intake()
        if not self.issue_description:
            return
        # Only auto-classify if AI provider is configured
        provider = self.env['ons.ai.provider'].sudo().search([
            ('name', '=', 'openai'),
            ('is_active', '=', True),
            ('provider_type', '=', 'chat'),
        ], limit=1)
        if not provider or not provider.api_key:
            return
        try:
            self.action_ai_classify()
        except Exception:
            _logger.warning("Auto-AI classify failed for %s, skipping.", self.name, exc_info=True)

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
