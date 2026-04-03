# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError


# ── Allowed transitions: from_code → {to_codes} ────────────────
ALLOWED_TRANSITIONS = {
    "intake_submitted": {"triage_in_progress", "callback_scheduled", "online_session_started", "onsite_dispatched", "closed_lost"},
    "triage_in_progress": {"callback_scheduled", "online_session_started", "onsite_dispatched", "closed_lost"},
    "callback_scheduled": {"online_session_started", "triage_in_progress", "closed_lost"},
    "online_session_started": {"handoff_to_assisting", "repair_in_progress", "closed_lost"},
    "handoff_to_assisting": {"repair_in_progress", "closed_lost"},
    "repair_in_progress": {"ready_for_verification", "handoff_to_assisting", "closed_lost"},
    "ready_for_verification": {"billing_in_progress", "repair_in_progress", "closed_lost"},
    "billing_in_progress": {"paid", "ready_for_verification", "closed_lost"},
    "paid": {"closed_won"},
    "onsite_dispatched": {"repair_in_progress", "closed_lost"},
    "closed_won": set(),
    "closed_lost": set(),
}


class Case(models.Model):
    _name = "ons.case"
    _description = "Service Case"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc, id desc"
    _rec_name = "name"

    # ── Identity ────────────────────────────────────────────────────
    name = fields.Char(
        string="Reference",
        readonly=True,
        default="New",
        copy=False,
        index=True,
    )
    partner_id = fields.Many2one(
        "res.partner",
        string="Customer",
        required=True,
        tracking=True,
        index=True,
    )
    partner_phone = fields.Char(related="partner_id.phone", string="Phone")

    # ── Stage ───────────────────────────────────────────────────────
    stage_id = fields.Many2one(
        "ons.case.stage",
        string="Stage",
        tracking=True,
        index=True,
        group_expand="_read_group_stage_ids",
        default=lambda self: self._default_stage(),
    )
    is_closed = fields.Boolean(related="stage_id.is_closed", store=True, index=True)
    is_won = fields.Boolean(related="stage_id.is_won", store=True)

    # ── Source links ────────────────────────────────────────────────
    source_interaction_id = fields.Many2one(
        "ons.interaction",
        string="Source Interaction",
        help="The interaction that created this case.",
    )
    interaction_ids = fields.One2many(
        "ons.interaction",
        "case_id",
        string="Related Interactions",
    )
    lead_id = fields.Many2one("crm.lead", string="CRM Lead", tracking=True, index=True)
    primary_driver_id = fields.Many2one(
        "ons.call.driver",
        string="Primary Driver",
        tracking=True,
        index=True,
    )

    # ── Relay fields from source interaction (for session tracker) ──
    call_status = fields.Selection(
        related="source_interaction_id.call_status",
        string="Call Status",
        readonly=False,
        store=True,
    )
    repair_status = fields.Selection(
        related="source_interaction_id.repair_status",
        string="Repair Status",
        readonly=False,
        store=True,
    )
    subject = fields.Char(
        related="source_interaction_id.subject",
        string="Subject",
        readonly=True,
        store=True,
    )

    # ── Assignment (3 roles) ────────────────────────────────────────
    intake_agent_id = fields.Many2one("res.users", string="Phone Technician", tracking=True, index=True)
    assigned_tech_id = fields.Many2one("res.users", string="Assisting Technician", tracking=True, index=True)
    billing_agent_id = fields.Many2one("res.users", string="Verification & Billing Tech (VBT)", tracking=True)

    # ── Details ─────────────────────────────────────────────────────
    issue_description = fields.Text(tracking=True)
    summary = fields.Text()
    next_action = fields.Char()
    next_action_at = fields.Datetime()
    online_session_started = fields.Boolean(tracking=True)

    # ── Aging ───────────────────────────────────────────────────────
    hours_in_pipeline = fields.Float(
        compute="_compute_aging",
        store=True,
        digits=(10, 1),
    )
    aging_bucket = fields.Selection(
        [
            ("0_4h", "0–4 hours"),
            ("4_24h", "4–24 hours"),
            ("24_48h", "1–2 days"),
            ("48_72h", "2–3 days"),
            ("72h_plus", "3+ days"),
        ],
        compute="_compute_aging",
        store=True,
    )
    is_stale = fields.Boolean(compute="_compute_aging", store=True)
    needs_attention = fields.Boolean(
        compute="_compute_needs_attention",
        store=True,
        index=True,
    )

    # ── History ─────────────────────────────────────────────────────
    stage_history_ids = fields.One2many(
        "ons.case.stage.history",
        "case_id",
        string="Stage History",
    )

    # ── Defaults / helpers ──────────────────────────────────────────
    @api.model
    def _default_stage(self):
        return self.env["ons.case.stage"].search([("code", "=", "intake_submitted")], limit=1)

    @api.model
    def _read_group_stage_ids(self, stages, domain):
        """Show all stages in kanban even when empty."""
        return self.env["ons.case.stage"].search([])

    # ── Sequence ────────────────────────────────────────────────────
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = self.env["ir.sequence"].next_by_code("ons.case") or "New"
        records = super().create(vals_list)
        # Log initial stage entry
        for rec in records:
            if rec.stage_id:
                self.env["ons.case.stage.history"].create({
                    "case_id": rec.id,
                    "stage_id": rec.stage_id.id,
                    "entered_at": fields.Datetime.now(),
                    "user_id": self.env.uid,
                })
        return records

    # ── Aging computation ───────────────────────────────────────────
    @api.depends("create_date", "is_closed")
    def _compute_aging(self):
        now = fields.Datetime.now()
        for rec in self:
            if not rec.create_date or rec.is_closed:
                rec.hours_in_pipeline = 0.0
                rec.aging_bucket = False
                rec.is_stale = False
                continue
            delta = now - rec.create_date
            hours = delta.total_seconds() / 3600.0
            rec.hours_in_pipeline = round(hours, 1)
            if hours <= 4:
                rec.aging_bucket = "0_4h"
            elif hours <= 24:
                rec.aging_bucket = "4_24h"
            elif hours <= 48:
                rec.aging_bucket = "24_48h"
            elif hours <= 72:
                rec.aging_bucket = "48_72h"
            else:
                rec.aging_bucket = "72h_plus"
            rec.is_stale = hours > 72

    @api.depends("is_closed", "assigned_tech_id", "stage_id", "is_stale")
    def _compute_needs_attention(self):
        """Flag cases that need human attention."""
        for rec in self:
            if rec.is_closed:
                rec.needs_attention = False
                continue
            # No tech assigned after intake
            needs_tech = (
                not rec.assigned_tech_id
                and rec.stage_id
                and rec.stage_id.code not in ("intake_submitted", "closed_won", "closed_lost")
            )
            rec.needs_attention = needs_tech or rec.is_stale

    # ── Stage transition ────────────────────────────────────────────
    def write(self, vals):
        if "stage_id" in vals:
            new_stage = self.env["ons.case.stage"].browse(vals["stage_id"])
            now = fields.Datetime.now()
            for rec in self:
                old_stage = rec.stage_id
                if old_stage and old_stage.id != new_stage.id:
                    self._validate_transition(old_stage, new_stage)
                    # Close previous history entry
                    last_history = self.env["ons.case.stage.history"].search([
                        ("case_id", "=", rec.id),
                        ("exited_at", "=", False),
                    ], limit=1, order="entered_at desc")
                    if last_history:
                        last_history.exited_at = now
                    # Create new history entry
                    self.env["ons.case.stage.history"].create({
                        "case_id": rec.id,
                        "stage_id": new_stage.id,
                        "entered_at": now,
                        "user_id": self.env.uid,
                    })
                    rec._hook_after_status_change(old_stage, new_stage)
        return super().write(vals)

    def _validate_transition(self, from_stage, to_stage):
        """Enforce allowed transitions from the matrix."""
        allowed = ALLOWED_TRANSITIONS.get(from_stage.code, set())
        if to_stage.code not in allowed:
            raise UserError(
                "Cannot move from '%s' to '%s'. This transition is not allowed."
                % (from_stage.name, to_stage.name)
            )

    # ── Business actions ────────────────────────────────────────────
    def action_force_stage(self, stage_code, notes=False):
        """Manager override — skip transition validation."""
        self.ensure_one()
        if not self.env.user.has_group("ons_ops_core.group_ops_manager"):
            raise UserError("Only managers can force a stage change.")
        new_stage = self.env["ons.case.stage"].search([("code", "=", stage_code)], limit=1)
        if not new_stage:
            raise UserError("Unknown stage code: %s" % stage_code)
        now = fields.Datetime.now()
        old_stage = self.stage_id
        # Close previous history
        last_history = self.env["ons.case.stage.history"].search([
            ("case_id", "=", self.id),
            ("exited_at", "=", False),
        ], limit=1, order="entered_at desc")
        if last_history:
            last_history.exited_at = now
        # Override history entry
        self.env["ons.case.stage.history"].create({
            "case_id": self.id,
            "stage_id": new_stage.id,
            "entered_at": now,
            "user_id": self.env.uid,
            "is_override": True,
            "notes": notes or "Forced from %s by %s" % (old_stage.name, self.env.user.name),
        })
        # Bypass write validation by calling super directly
        super(Case, self).write({"stage_id": new_stage.id})

    def action_reopen(self):
        """Reopen a closed case back to triage_in_progress."""
        for rec in self:
            if not rec.is_closed:
                raise UserError("Case is not closed.")
            triage = self.env["ons.case.stage"].search([("code", "=", "triage_in_progress")], limit=1)
            if not triage:
                raise UserError("Triage stage not found.")
            now = fields.Datetime.now()
            last_history = self.env["ons.case.stage.history"].search([
                ("case_id", "=", rec.id),
                ("exited_at", "=", False),
            ], limit=1, order="entered_at desc")
            if last_history:
                last_history.exited_at = now
            self.env["ons.case.stage.history"].create({
                "case_id": rec.id,
                "stage_id": triage.id,
                "entered_at": now,
                "user_id": self.env.uid,
                "is_override": True,
                "notes": "Reopened by %s" % self.env.user.name,
            })
            super(Case, rec).write({"stage_id": triage.id})

    # ── Connector hooks ─────────────────────────────────────────────
    def _hook_after_status_change(self, old_stage, new_stage):
        """Extension point for connectors (Discord notifications, etc.).
        Override in sub-modules to add side effects on stage transition."""
        pass

    # ── Auto-detect assisting tech from chatter ─────────────────────
    def message_post(self, **kwargs):
        """Auto-set assisting tech when a non-intake user posts a note."""
        result = super().message_post(**kwargs)
        if kwargs.get("message_type") == "comment" and kwargs.get("subtype_xmlid") == "mail.mt_note":
            author_uid = self.env.uid
            for rec in self:
                if (
                    not rec.assigned_tech_id
                    and rec.intake_agent_id
                    and author_uid != rec.intake_agent_id.id
                ):
                    rec.assigned_tech_id = author_uid
        return result
