from odoo import fields, models


class AiModel(models.Model):
    _name = 'ons.ai.model'
    _description = 'AI Model Catalog'
    _order = 'provider_id, category, model_id'

    model_id = fields.Char(
        string='Model ID', required=True,
        help='Provider model identifier, e.g. gpt-4o, whisper-1',
    )
    display_name_custom = fields.Char(string='Display Name')
    provider_id = fields.Many2one('ons.ai.provider', required=True, ondelete='restrict')
    category = fields.Selection([
        ('chat', 'Chat'),
        ('reasoning', 'Reasoning'),
        ('transcription', 'Transcription'),
        ('embedding', 'Embedding'),
        ('tts', 'Text-to-Speech'),
    ], required=True, default='chat')
    capabilities = fields.Text(
        help='One capability per line: reasoning, fast, cheap, vision, etc.',
    )
    pricing_tier = fields.Selection([
        ('budget', 'Budget'),
        ('standard', 'Standard'),
        ('premium', 'Premium'),
    ], default='standard')
    input_cost_per_1k = fields.Float(string='Input Cost / 1k tokens', digits=(10, 6))
    output_cost_per_1k = fields.Float(string='Output Cost / 1k tokens', digits=(10, 6))
    max_tokens = fields.Integer()
    context_window = fields.Integer()
    is_available = fields.Boolean(default=True)

    _model_id_unique = models.UniqueIndex('(model_id)', 'Model ID must be unique.')

    def _compute_display_name(self):
        for rec in self:
            rec.display_name = rec.display_name_custom or rec.model_id

    def name_get(self):
        return [(r.id, r.display_name_custom or r.model_id) for r in self]
