from odoo import fields, models


class QaCallTypeRule(models.Model):
    _name = "ons.qa.call.type.rule"
    _description = "QA Call Type → Rule Mapping"
    _order = "phase, sequence"

    _rule_per_type_unique = models.UniqueIndex(
        "(call_type_id, rule_id)",
        "Each rule can only be mapped once per call type.",
    )

    call_type_id = fields.Many2one(
        "ons.qa.call.type", required=True, ondelete="cascade", index=True,
    )
    rule_id = fields.Many2one(
        "ons.qa.rule", required=True, ondelete="cascade", index=True,
    )
    phase = fields.Char(help="Override phase from rule default")
    applicability = fields.Selection(
        [
            ("required", "Required"),
            ("optional", "Optional"),
            ("forbidden", "Forbidden"),
            ("not_applicable", "Not Applicable"),
        ],
        required=True,
        default="required",
    )
    points_override = fields.Integer(help="Override default rule points")
    is_active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)
