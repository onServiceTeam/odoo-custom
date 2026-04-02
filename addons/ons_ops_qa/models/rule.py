from odoo import fields, models


class QaRule(models.Model):
    _name = "ons.qa.rule"
    _description = "QA Scoring Rule"
    _order = "phase, display_order, name"

    _key_unique = models.UniqueIndex("(key)", "Rule key must be unique.")

    key = fields.Char(required=True, index=True)
    name = fields.Char(required=True)
    rule_type = fields.Selection(
        [
            ("required", "Required"),
            ("forbidden", "Forbidden"),
            ("sequence", "Sequence"),
            ("call_control", "Call Control"),
        ],
        required=True,
        default="required",
    )
    check_type = fields.Selection(
        [
            ("phrase_present", "Phrase Present"),
            ("phrase_absent", "Phrase Absent"),
            ("sequence_order", "Sequence Order"),
            ("talk_time", "Talk Time"),
            ("manual", "Manual"),
        ],
        required=True,
        default="manual",
    )
    phase = fields.Char(index=True, help="Call phase this rule belongs to")
    points = fields.Integer(default=1, help="Points awarded if passed")
    penalty_points = fields.Integer(default=0, help="Points deducted if failed")
    is_auto_fail = fields.Boolean(help="Triggers auto-fail on violation")
    score_cap = fields.Integer(
        default=40,
        help="Maximum score allowed if auto-fail triggered",
    )
    coaching_text = fields.Text(help="Coaching explanation for this rule")
    coaching_examples = fields.Text(help="Good and bad examples")
    is_active = fields.Boolean(default=True)
    display_order = fields.Integer(default=10)
