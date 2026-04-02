import re

from odoo import api, fields, models


class AiPromptTemplate(models.Model):
    _name = 'ons.ai.prompt.template'
    _description = 'AI Prompt Contract / Template'
    _order = 'task_type, version desc'

    code = fields.Char(required=True, help='Unique machine key for this prompt')
    name = fields.Char(required=True)
    task_type = fields.Char(
        required=True,
        help='Links to ons.ai.task.task_type',
    )
    system_prompt = fields.Text(
        required=True,
        help='System message. Supports {{variable}} placeholders.',
    )
    user_prompt_template = fields.Text(
        help='User message template. Supports {{variable}} placeholders.',
    )
    available_variables = fields.Text(
        help='Documentation of available variables for this prompt.',
    )
    version = fields.Integer(default=1, required=True)
    is_active = fields.Boolean(default=True)

    _sql_constraints = [
        ('unique_code_version', 'UNIQUE(code, version)', 'Code + version must be unique.'),
    ]

    @api.model
    def render(self, code, variables=None):
        """Render a prompt template by code, returning system and user prompts.

        Returns dict with 'system_prompt' and 'user_prompt' keys.
        Variables are interpolated using {{key}} syntax.
        """
        template = self.search([
            ('code', '=', code),
            ('is_active', '=', True),
        ], order='version desc', limit=1)
        if not template:
            return {'system_prompt': '', 'user_prompt': '', 'version': 0}
        variables = variables or {}
        system = self._interpolate(template.system_prompt, variables)
        user = self._interpolate(template.user_prompt_template or '', variables)
        return {
            'system_prompt': system,
            'user_prompt': user,
            'version': template.version,
            'template_id': template.id,
        }

    @staticmethod
    def _interpolate(text, variables):
        """Replace {{key}} placeholders with variable values.

        Missing variables are left as-is (not stripped).
        """
        if not text:
            return ''

        def _replacer(match):
            key = match.group(1).strip()
            return str(variables.get(key, match.group(0)))

        return re.sub(r'\{\{(\s*\w+\s*)\}\}', _replacer, text)

    def action_new_version(self):
        """Create a new version of this prompt, deactivating the current one."""
        self.ensure_one()
        new = self.copy({
            'version': self.version + 1,
            'is_active': True,
        })
        self.is_active = False
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'ons.ai.prompt.template',
            'res_id': new.id,
            'view_mode': 'form',
            'target': 'current',
        }
