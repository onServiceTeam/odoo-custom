from odoo import fields, models


class QaFinding(models.Model):
    _name = "ons.qa.finding"
    _description = "QA Finding / Evidence"
    _order = "phase, sequence"

    result_id = fields.Many2one(
        "ons.qa.result", required=True, ondelete="cascade", index=True,
    )
    rule_key = fields.Char(index=True)
    rule_name = fields.Char()
    phase = fields.Char(index=True)
    finding_type = fields.Selection(
        [
            ("behavior", "Behavior"),
            ("forbidden_word", "Forbidden Word"),
            ("policy_violation", "Policy Violation"),
            ("sequence", "Sequence"),
        ],
        default="behavior",
    )
    severity = fields.Selection(
        [
            ("low", "Low"),
            ("medium", "Medium"),
            ("high", "High"),
            ("critical", "Critical"),
        ],
        default="medium",
    )
    status = fields.Selection(
        [
            ("hit", "Hit"),
            ("missed", "Missed"),
            ("partial", "Partial"),
            ("not_applicable", "N/A"),
            ("needs_review", "Needs Review"),
        ],
        required=True,
        default="hit",
    )

    # ── Evidence ────────────────────────────────────────────────
    evidence_quote = fields.Text()
    evidence_start_ms = fields.Integer(string="Evidence Start (ms)")
    evidence_end_ms = fields.Integer(string="Evidence End (ms)")
    evidence_speaker = fields.Selection(
        [("agent", "Agent"), ("customer", "Customer"), ("unknown", "Unknown")],
    )

    # ── Scoring ─────────────────────────────────────────────────
    points_earned = fields.Float(digits=(5, 2))
    points_possible = fields.Float(digits=(5, 2))

    # ── Verification ────────────────────────────────────────────
    needs_human_review = fields.Boolean()
    verified_by = fields.Many2one("res.users", readonly=True)
    verified_at = fields.Datetime(readonly=True)
    verification_notes = fields.Text()

    sequence = fields.Integer(default=10)
