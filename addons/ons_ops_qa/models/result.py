from odoo import api, fields, models
from odoo.exceptions import UserError


class QaResult(models.Model):
    _name = "ons.qa.result"
    _description = "QA Evaluation Result"
    _order = "create_date desc"
    _inherit = ["mail.thread"]

    # ── Core links ──────────────────────────────────────────────
    call_log_id = fields.Many2one(
        "ons.call.log", required=True, ondelete="restrict", index=True,
        tracking=True,
    )
    agent_id = fields.Many2one(
        "res.users", string="Agent", compute="_compute_agent_id",
        store=True, index=True,
    )
    evaluator_id = fields.Many2one(
        "res.users", string="Evaluator", default=lambda self: self.env.uid,
        tracking=True,
    )
    interaction_id = fields.Many2one(
        "ons.interaction", compute="_compute_links", store=True,
    )
    case_id = fields.Many2one(
        "ons.case", compute="_compute_links", store=True,
    )

    # ── Call type ───────────────────────────────────────────────
    call_type_id = fields.Many2one(
        "ons.qa.call.type", string="Call Type", tracking=True,
    )

    # ── Scoring ─────────────────────────────────────────────────
    final_score = fields.Float(digits=(5, 2), tracking=True)
    auto_fail = fields.Boolean(tracking=True)
    auto_fail_reasons = fields.Text()
    score_cap = fields.Integer()
    phase_scores_json = fields.Text(string="Phase Scores (JSON)")
    rule_results_json = fields.Text(string="Rule Results (JSON)")
    global_violations_json = fields.Text(string="Global Violations (JSON)")
    operational_summary = fields.Text()
    coaching_summary = fields.Text()

    # ── Workflow state ──────────────────────────────────────────
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("graded", "Graded"),
            ("in_review", "In Review"),
            ("reviewed", "Reviewed"),
            ("ack_pending", "Awaiting Acknowledgement"),
            ("acknowledged", "Acknowledged"),
            ("disputed", "Disputed"),
        ],
        default="draft",
        required=True,
        tracking=True,
        index=True,
    )
    needs_human_review = fields.Boolean()
    human_review_reasons = fields.Text()

    # ── Review ──────────────────────────────────────────────────
    reviewed_at = fields.Datetime(readonly=True)
    reviewed_by = fields.Many2one("res.users", string="Reviewed By", readonly=True)
    review_notes = fields.Text()
    override_score = fields.Float(digits=(5, 2), tracking=True)

    # ── Acknowledgement ─────────────────────────────────────────
    acknowledged_at = fields.Datetime(readonly=True)
    dispute_reason = fields.Text()

    # ── Children ────────────────────────────────────────────────
    finding_ids = fields.One2many("ons.qa.finding", "result_id", string="Findings")
    finding_count = fields.Integer(compute="_compute_finding_count")
    coaching_id = fields.Many2one("ons.qa.coaching", string="Coaching", readonly=True)
    ai_run_ids = fields.One2many(
        "ons.ai.run", "res_id",
        domain=[("res_model", "=", "ons.qa.result")],
        string="AI Runs",
    )

    # ── Computed ────────────────────────────────────────────────
    effective_score = fields.Float(
        digits=(5, 2), compute="_compute_effective_score", store=True,
    )

    @api.depends("call_log_id", "call_log_id.agent_id")
    def _compute_agent_id(self):
        for rec in self:
            rec.agent_id = rec.call_log_id.agent_id

    @api.depends("call_log_id", "call_log_id.interaction_id", "call_log_id.interaction_id.case_id")
    def _compute_links(self):
        for rec in self:
            interaction = rec.call_log_id.interaction_id
            rec.interaction_id = interaction.id if interaction else False
            rec.case_id = interaction.case_id.id if interaction and interaction.case_id else False

    @api.depends("finding_ids")
    def _compute_finding_count(self):
        for rec in self:
            rec.finding_count = len(rec.finding_ids)

    @api.depends("final_score", "override_score")
    def _compute_effective_score(self):
        for rec in self:
            rec.effective_score = rec.override_score if rec.override_score else rec.final_score

    # ── Workflow actions ────────────────────────────────────────
    def action_grade(self, score, auto_fail=False, auto_fail_reasons="", score_cap=0):
        """Grade the evaluation with a score. Advances state."""
        self.ensure_one()
        if self.state != "draft":
            raise UserError("Can only grade evaluations in draft state.")
        vals = {
            "final_score": max(0.0, min(100.0, score)),
            "auto_fail": auto_fail,
            "auto_fail_reasons": auto_fail_reasons,
            "score_cap": score_cap,
        }
        if auto_fail and score_cap:
            vals["final_score"] = min(vals["final_score"], score_cap)
        if auto_fail or self.needs_human_review:
            vals["state"] = "in_review"
            vals["needs_human_review"] = True
        else:
            vals["state"] = "ack_pending"
        self.write(vals)

    def action_send_to_review(self):
        """Manually send a graded result to manager review."""
        self.ensure_one()
        if self.state not in ("graded", "ack_pending"):
            raise UserError("Can only send graded or pending results to review.")
        self.write({"state": "in_review", "needs_human_review": True})

    def action_review(self, notes="", override_score=0.0):
        """Manager reviews the evaluation."""
        self.ensure_one()
        if self.state not in ("in_review", "disputed"):
            raise UserError("Can only review evaluations that are in review or disputed.")
        vals = {
            "state": "ack_pending",
            "reviewed_at": fields.Datetime.now(),
            "reviewed_by": self.env.uid,
            "review_notes": notes,
        }
        if override_score:
            vals["override_score"] = max(0.0, min(100.0, override_score))
        self.write(vals)

    def action_acknowledge(self):
        """Agent acknowledges the evaluation."""
        self.ensure_one()
        if self.state != "ack_pending":
            raise UserError("Can only acknowledge evaluations awaiting acknowledgement.")
        if self.env.uid != self.agent_id.id:
            raise UserError("Only the evaluated agent can acknowledge this result.")
        self.write({
            "state": "acknowledged",
            "acknowledged_at": fields.Datetime.now(),
        })

    def action_dispute(self, reason):
        """Agent disputes the evaluation."""
        self.ensure_one()
        if self.state != "ack_pending":
            raise UserError("Can only dispute evaluations awaiting acknowledgement.")
        if self.env.uid != self.agent_id.id:
            raise UserError("Only the evaluated agent can dispute this result.")
        if not reason or not reason.strip():
            raise UserError("Dispute reason is required.")
        self.write({
            "state": "in_review",
            "dispute_reason": reason.strip(),
        })

    def action_generate_coaching(self):
        """Create a coaching artifact stub for this result."""
        self.ensure_one()
        if self.coaching_id:
            raise UserError("Coaching already exists for this evaluation.")
        if self.state == "draft":
            raise UserError("Cannot generate coaching for a draft evaluation.")
        coaching = self.env["ons.qa.coaching"].create({
            "result_id": self.id,
            "priority": "medium",
            "state": "draft",
        })
        self.write({"coaching_id": coaching.id})
        return coaching

    def action_view_findings(self):
        """Open findings list filtered by this result."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Findings",
            "res_model": "ons.qa.finding",
            "view_mode": "list,form",
            "domain": [("result_id", "=", self.id)],
            "context": {"default_result_id": self.id},
        }
