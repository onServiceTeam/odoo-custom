from odoo import api, fields, models
from odoo.exceptions import UserError


class QaCoaching(models.Model):
    _name = "ons.qa.coaching"
    _description = "QA Coaching Artifact"
    _order = "create_date desc"

    result_id = fields.Many2one(
        "ons.qa.result", required=True, ondelete="cascade", index=True,
    )
    agent_id = fields.Many2one(
        "res.users", compute="_compute_agent_id", store=True,
    )
    priority = fields.Selection(
        [
            ("low", "Low"),
            ("medium", "Medium"),
            ("high", "High"),
            ("critical", "Critical"),
        ],
        default="medium",
    )
    quality = fields.Selection(
        [
            ("rich", "Rich"),
            ("generic", "Generic"),
            ("insufficient_data", "Insufficient Data"),
        ],
    )
    summary = fields.Text()
    strengths_json = fields.Text(string="Strengths (JSON)")
    improvements_json = fields.Text(string="Improvements (JSON)")
    action_steps_json = fields.Text(string="Action Steps (JSON)")
    example_phrases_json = fields.Text(string="Example Phrases (JSON)")
    manager_notes = fields.Text()
    ai_run_id = fields.Many2one("ons.ai.run", string="AI Run", readonly=True)
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("published", "Published"),
            ("acknowledged", "Acknowledged"),
        ],
        default="draft",
        required=True,
        index=True,
    )

    @api.depends("result_id", "result_id.agent_id")
    def _compute_agent_id(self):
        for rec in self:
            rec.agent_id = rec.result_id.agent_id

    def action_publish(self):
        """Publish coaching so agent can see it."""
        self.ensure_one()
        if self.state != "draft":
            raise UserError("Can only publish draft coaching.")
        if not self.summary:
            raise UserError("Coaching summary is required before publishing.")
        self.write({"state": "published"})

    def action_acknowledge_coaching(self):
        """Agent acknowledges they have read the coaching."""
        self.ensure_one()
        if self.state != "published":
            raise UserError("Can only acknowledge published coaching.")
        if self.env.uid != self.agent_id.id:
            raise UserError("Only the coached agent can acknowledge.")
        self.write({"state": "acknowledged"})
