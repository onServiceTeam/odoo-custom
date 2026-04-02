from odoo import api, fields, models
from odoo.exceptions import UserError


class AiTask(models.Model):
    _name = 'ons.ai.task'
    _description = 'AI Task → Model Routing'
    _order = 'task_type'

    task_type = fields.Char(
        required=True,
        help='Machine key, e.g. intake_classification, description_polish',
    )
    display_name_custom = fields.Char(string='Display Name')
    description = fields.Text()
    model_id = fields.Many2one(
        'ons.ai.model', string='Primary Model',
        required=True, ondelete='restrict',
    )
    fallback_model_id = fields.Many2one(
        'ons.ai.model', string='Fallback Model',
        ondelete='set null',
    )
    temperature = fields.Float(default=0.3, digits=(3, 2))
    max_tokens = fields.Integer(default=4000)
    is_enabled = fields.Boolean(default=True)
    prompt_template_id = fields.Many2one(
        'ons.ai.prompt.template', string='Prompt Template',
        ondelete='set null',
    )

    _task_type_unique = models.UniqueIndex('(task_type)', 'Task type must be unique.')

    def _compute_display_name(self):
        for rec in self:
            rec.display_name = rec.display_name_custom or rec.task_type

    @api.model
    def get_task_config(self, task_type):
        """Return task configuration for sidecar consumption.

        Called by the sidecar to retrieve the Odoo-managed routing config.
        If the task is disabled or missing, raises UserError.
        """
        task = self.search([('task_type', '=', task_type)], limit=1)
        if not task:
            raise UserError(f'AI task "{task_type}" is not configured.')
        if not task.is_enabled:
            raise UserError(f'AI task "{task_type}" is disabled.')
        return {
            'task_type': task.task_type,
            'model_id': task.model_id.model_id,
            'fallback_model_id': task.fallback_model_id.model_id if task.fallback_model_id else False,
            'temperature': task.temperature,
            'max_tokens': task.max_tokens,
        }
