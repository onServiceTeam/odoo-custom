import json
import logging
import time

import requests

from odoo import api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AiProvider(models.Model):
    _name = 'ons.ai.provider'
    _description = 'AI Provider Configuration'
    _order = 'provider_type, name'

    name = fields.Char(required=True, help='Machine key, e.g. openai, anthropic')
    display_name_custom = fields.Char(string='Display Name')
    provider_type = fields.Selection([
        ('chat', 'Chat / Completion'),
        ('transcription', 'Transcription'),
        ('embedding', 'Embedding'),
        ('tts', 'Text-to-Speech'),
    ], required=True, default='chat')
    api_endpoint = fields.Char(string='API Endpoint')
    api_key = fields.Char(
        string='API Key',
        groups='ons_ops_core.group_ops_manager',
        help='API key for this provider. Only visible to managers.',
    )
    is_active = fields.Boolean(default=False)
    config_json = fields.Text(
        string='Configuration (JSON)',
        help='Encrypted config blob — API keys managed by sidecar, '
             'not stored in plain text here.',
    )
    last_health_check = fields.Datetime(readonly=True)
    health_status = fields.Selection([
        ('unknown', 'Unknown'),
        ('healthy', 'Healthy'),
        ('degraded', 'Degraded'),
        ('down', 'Down'),
    ], default='unknown', readonly=True)

    model_ids = fields.One2many('ons.ai.model', 'provider_id', string='Models')

    _name_unique = models.UniqueIndex('(name)', 'Provider name must be unique.')

    @api.depends('display_name_custom', 'name')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = rec.display_name_custom or rec.name

    def action_mark_healthy(self):
        self.write({
            'last_health_check': fields.Datetime.now(),
            'health_status': 'healthy',
        })

    def action_mark_down(self):
        self.write({
            'last_health_check': fields.Datetime.now(),
            'health_status': 'down',
        })

    def action_test_connection(self):
        """Send a lightweight test request to verify the API key works."""
        self.ensure_one()
        if not self.api_key:
            raise UserError("Set an API key first.")
        try:
            result = self._call_api(
                model_id='gpt-4o-mini',
                system_prompt='Reply with exactly: OK',
                user_prompt='Test',
                max_tokens=5,
                temperature=0,
            )
            self.action_mark_healthy()
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Connection Successful',
                    'message': 'API responded: %s' % result.get('content', '')[:50],
                    'type': 'success',
                },
            }
        except Exception as e:
            self.action_mark_down()
            raise UserError("Connection failed: %s" % str(e))

    def _call_api(self, model_id, system_prompt, user_prompt, max_tokens=4000, temperature=0.3):
        """Call the provider's chat completion API.

        Returns dict with keys: content, input_tokens, output_tokens, model_used.
        """
        self.ensure_one()
        if not self.api_key:
            raise UserError("No API key configured for provider '%s'." % self.name)
        if not self.api_endpoint:
            raise UserError("No API endpoint configured for provider '%s'." % self.name)

        headers = {
            'Authorization': 'Bearer %s' % self.api_key,
            'Content-Type': 'application/json',
        }
        payload = {
            'model': model_id,
            'messages': [
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_prompt},
            ],
            'max_tokens': max_tokens,
            'temperature': temperature,
        }

        start = time.time()
        try:
            resp = requests.post(
                self.api_endpoint,
                headers=headers,
                json=payload,
                timeout=60,
            )
            resp.raise_for_status()
        except requests.exceptions.Timeout:
            raise UserError("AI API request timed out after 60 seconds.")
        except requests.exceptions.HTTPError as e:
            body = ''
            try:
                body = e.response.json().get('error', {}).get('message', '')
            except Exception:
                body = e.response.text[:200]
            raise UserError("AI API error (%s): %s" % (e.response.status_code, body))
        except requests.exceptions.ConnectionError:
            raise UserError("Cannot connect to AI API at %s" % self.api_endpoint)

        duration_ms = int((time.time() - start) * 1000)
        data = resp.json()
        choice = data.get('choices', [{}])[0]
        usage = data.get('usage', {})

        return {
            'content': choice.get('message', {}).get('content', ''),
            'input_tokens': usage.get('prompt_tokens', 0),
            'output_tokens': usage.get('completion_tokens', 0),
            'model_used': data.get('model', model_id),
            'duration_ms': duration_ms,
        }
