from odoo import api, fields, models


class AiRun(models.Model):
    _name = 'ons.ai.run'
    _description = 'AI Run Audit Log'
    _order = 'create_date desc'

    task_type = fields.Char(required=True, index=True)
    model_id = fields.Many2one('ons.ai.model', ondelete='set null')
    requested_model = fields.Char(help='Model ID requested by the task')
    actual_model = fields.Char(help='Model ID actually used by the provider')
    model_mismatch = fields.Boolean(
        compute='_compute_model_mismatch', store=True,
    )
    input_tokens = fields.Integer()
    output_tokens = fields.Integer()
    total_cost = fields.Float(digits=(10, 6))
    duration_ms = fields.Integer(string='Duration (ms)')
    success = fields.Boolean(default=True)
    error_message = fields.Text()

    # Polymorphic link to source record
    res_model = fields.Char(string='Source Model', index=True)
    res_id = fields.Many2oneReference(
        string='Source Record', model_field='res_model',
    )

    user_id = fields.Many2one('res.users', default=lambda s: s.env.uid)
    prompt_template_id = fields.Many2one('ons.ai.prompt.template', ondelete='set null')
    prompt_version = fields.Integer()

    request_summary = fields.Text(help='Truncated input (first 500 chars)')
    response_summary = fields.Text(help='Truncated output (first 500 chars)')

    @api.depends('requested_model', 'actual_model')
    def _compute_model_mismatch(self):
        for rec in self:
            rec.model_mismatch = bool(
                rec.requested_model
                and rec.actual_model
                and rec.requested_model != rec.actual_model
            )

    @api.model
    def log_run(self, vals):
        """Create a run log entry. Called by the sidecar after each AI call.

        Truncates request/response summaries to 500 chars.
        Returns the created record id.
        """
        if vals.get('request_summary'):
            vals['request_summary'] = vals['request_summary'][:500]
        if vals.get('response_summary'):
            vals['response_summary'] = vals['response_summary'][:500]
        run = self.sudo().create(vals)
        return run.id
