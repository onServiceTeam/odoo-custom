from odoo import api, fields, models


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
