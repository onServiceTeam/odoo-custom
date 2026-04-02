from odoo import api, fields, models


class QaCallType(models.Model):
    _name = "ons.qa.call.type"
    _description = "QA Call Type"
    _order = "detection_priority desc, name"

    _name_unique = models.UniqueIndex("(key)", "Call type key must be unique.")

    key = fields.Char(required=True, index=True)
    name = fields.Char(required=True)
    description = fields.Text()
    phases = fields.Text(
        help="Comma-separated ordered phase names, e.g. call_control,opening,foundations",
    )
    phase_weights_json = fields.Text(
        string="Phase Weights (JSON)",
        help='JSON mapping phase→weight. Weights must sum to 100. e.g. {"call_control":15,"opening":10}',
    )
    detection_priority = fields.Integer(default=10)
    is_active = fields.Boolean(default=True)
    rule_ids = fields.One2many("ons.qa.call.type.rule", "call_type_id", string="Rule Mappings")
    rule_count = fields.Integer(compute="_compute_rule_count")

    @api.depends("rule_ids")
    def _compute_rule_count(self):
        for rec in self:
            rec.rule_count = len(rec.rule_ids)

    def get_phases_list(self):
        """Return ordered list of phase names."""
        self.ensure_one()
        if not self.phases:
            return []
        return [p.strip() for p in self.phases.split(",") if p.strip()]

    def get_phase_weights(self):
        """Return dict of phase→weight from JSON."""
        import json
        self.ensure_one()
        if not self.phase_weights_json:
            return {}
        try:
            return json.loads(self.phase_weights_json)
        except (json.JSONDecodeError, TypeError):
            return {}
