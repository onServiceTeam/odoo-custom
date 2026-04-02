# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError


# ── Allowed transitions: from_code → {to_codes} ────────────────
ALLOWED_TRANSITIONS = {
    "draft": {"pending_approval", "sent", "cancelled", "voided"},
    "pending_approval": {"sent", "cancelled", "voided"},
    "sent": {"has_applicants", "cancelled", "voided"},
    "has_applicants": {"assigned", "cancelled", "voided"},
    "assigned": {"confirmed", "cancelled", "voided"},
    "confirmed": {"in_progress", "cancelled", "voided"},
    "in_progress": {"completed", "cancelled"},
    "completed": set(),
    "cancelled": set(),
    "voided": set(),
}

# Statuses where voiding is NOT allowed (worker already assigned)
NO_VOID = {"assigned", "confirmed", "in_progress", "completed", "cancelled", "voided"}


class Dispatch(models.Model):
    _name = "ons.dispatch"
    _description = "Dispatch / Onsite Assignment"
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
    title = fields.Char(
        string="Job Title",
        required=True,
        tracking=True,
        help="E.g. 'On-Site Computer Repair — Austin'",
    )
    description = fields.Text(tracking=True)
    special_instructions = fields.Text(help="Private notes for the technician.")

    # ── Status ──────────────────────────────────────────────────────
    status_id = fields.Many2one(
        "ons.dispatch.status",
        string="Status",
        tracking=True,
        index=True,
        default=lambda self: self._default_status(),
        group_expand="_read_group_status_ids",
    )
    dispatch_status = fields.Char(
        related="status_id.code",
        string="Status Code",
        store=True,
        index=True,
    )
    is_terminal = fields.Boolean(related="status_id.is_terminal", store=True)

    # ── Case / source links ─────────────────────────────────────────
    case_id = fields.Many2one(
        "ons.case",
        string="Service Case",
        tracking=True,
        index=True,
        ondelete="set null",
    )
    partner_id = fields.Many2one(
        "res.partner",
        string="Customer",
        tracking=True,
        index=True,
    )

    # ── Location ────────────────────────────────────────────────────
    location_type = fields.Selection(
        [("residential", "Residential"), ("commercial", "Commercial")],
        default="residential",
    )
    street = fields.Char()
    street2 = fields.Char()
    city = fields.Char()
    state_id = fields.Many2one("res.country.state", string="State")
    zip = fields.Char(string="ZIP")
    country_id = fields.Many2one("res.country", string="Country")
    address_validated = fields.Boolean(default=False)
    address_lat = fields.Float(digits=(10, 7))
    address_lng = fields.Float(digits=(10, 7))

    # ── Contact ─────────────────────────────────────────────────────
    contact_first_name = fields.Char()
    contact_last_name = fields.Char()
    contact_phone = fields.Char()
    contact_extension = fields.Char()
    customer_timezone = fields.Selection(
        "_tz_list",
        default="America/New_York",
    )

    @api.model
    def _tz_list(self):
        import pytz
        return [(tz, tz) for tz in sorted(pytz.common_timezones)]

    # ── Schedule ────────────────────────────────────────────────────
    scheduled_start = fields.Datetime(string="Scheduled Start", tracking=True)
    scheduled_end = fields.Datetime(string="Scheduled End")

    # ── Pricing ─────────────────────────────────────────────────────
    budget = fields.Monetary(currency_field="currency_id")
    currency_id = fields.Many2one(
        "res.currency",
        default=lambda self: self.env.company.currency_id,
    )
    pricing_type = fields.Selection(
        [
            ("flat", "Flat Rate"),
            ("per_hour", "Per Hour"),
            ("per_unit", "Per Unit"),
            ("internal", "Internal"),
        ],
        default="flat",
    )
    payment_terms = fields.Selection(
        [
            ("immediately", "Immediately"),
            ("7_days", "7 Days"),
            ("15_days", "15 Days"),
            ("21_days", "21 Days"),
            ("30_days", "30 Days"),
        ],
        default="15_days",
    )

    # ── Assignment ──────────────────────────────────────────────────
    assigned_worker_name = fields.Char(string="Assigned Worker")
    assigned_worker_id = fields.Char(string="External Worker ID", index=True)

    # ── Approval ────────────────────────────────────────────────────
    requires_approval = fields.Boolean(default=False)
    approved_by = fields.Many2one("res.users", string="Approved By")
    approved_at = fields.Datetime()

    # ── Lifecycle timestamps ────────────────────────────────────────
    confirmed_at = fields.Datetime()
    started_at = fields.Datetime()
    completed_at = fields.Datetime()
    cancelled_at = fields.Datetime()
    voided_at = fields.Datetime()

    # ── Cancellation ────────────────────────────────────────────────
    cancellation_reason_id = fields.Many2one(
        "ons.dispatch.cancellation.reason",
        string="Cancellation Reason",
    )
    cancellation_reason = fields.Text(string="Cancellation Notes")
    void_reason = fields.Text(string="Void Reason")

    # ── External marketplace ────────────────────────────────────────
    wm_assignment_id = fields.Char(
        string="WorkMarket Assignment ID",
        index=True,
        copy=False,
    )

    # ── Child records ───────────────────────────────────────────────
    applicant_ids = fields.One2many("ons.dispatch.applicant", "dispatch_id", string="Applicants")
    checklist_ids = fields.One2many("ons.dispatch.checklist.item", "dispatch_id", string="Checklist")
    reminder_ids = fields.One2many("ons.dispatch.reminder", "dispatch_id", string="Reminders")
    voice_call_ids = fields.One2many("ons.dispatch.voice.call", "dispatch_id", string="Voice Calls")
    activity_log_ids = fields.One2many("ons.dispatch.activity.log", "dispatch_id", string="Activity Log")

    # ── Computed ────────────────────────────────────────────────────
    applicant_count = fields.Integer(compute="_compute_counts")
    pending_applicant_count = fields.Integer(compute="_compute_counts")
    checklist_progress = fields.Float(compute="_compute_checklist_progress")
    needs_action = fields.Boolean(compute="_compute_needs_action", store=True, index=True)

    @api.depends("applicant_ids", "applicant_ids.status")
    def _compute_counts(self):
        for rec in self:
            rec.applicant_count = len(rec.applicant_ids)
            rec.pending_applicant_count = len(rec.applicant_ids.filtered(lambda a: a.status == "pending"))

    @api.depends("checklist_ids", "checklist_ids.completed")
    def _compute_checklist_progress(self):
        for rec in self:
            total = len(rec.checklist_ids)
            done = len(rec.checklist_ids.filtered("completed"))
            rec.checklist_progress = (done / total * 100) if total else 0.0

    @api.depends("dispatch_status", "applicant_ids.status")
    def _compute_needs_action(self):
        for rec in self:
            rec.needs_action = (
                rec.dispatch_status == "has_applicants"
                or (
                    rec.dispatch_status == "sent"
                    and any(a.status == "pending" for a in rec.applicant_ids)
                )
            )

    # ── Defaults / helpers ──────────────────────────────────────────
    @api.model
    def _default_status(self):
        return self.env["ons.dispatch.status"].search([("code", "=", "draft")], limit=1)

    @api.model
    def _read_group_status_ids(self, statuses, domain):
        return self.env["ons.dispatch.status"].search([])

    # ── Sequence ────────────────────────────────────────────────────
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = self.env["ir.sequence"].next_by_code("ons.dispatch") or "New"
        records = super().create(vals_list)
        for rec in records:
            rec._create_default_checklist()
            rec._log_activity("created", "Dispatch created")
        return records

    # ── Status transition ───────────────────────────────────────────
    def action_change_status(self, new_code, **kwargs):
        """Move to a new status with validation."""
        self.ensure_one()
        current_code = self.dispatch_status

        if current_code not in ALLOWED_TRANSITIONS:
            raise UserError("Unknown current status: %s" % current_code)

        allowed = ALLOWED_TRANSITIONS[current_code]
        if new_code not in allowed:
            raise UserError(
                "Cannot move from '%s' to '%s'. Allowed: %s"
                % (current_code, new_code, ", ".join(sorted(allowed)) or "none")
            )

        # Specific validations
        if new_code == "voided" and current_code in NO_VOID:
            raise UserError("Cannot void a dispatch that has been assigned to a worker.")

        if new_code == "cancelled" and not kwargs.get("reason"):
            raise UserError("Cancellation reason is required.")

        if new_code == "sent" and current_code == "pending_approval":
            if not self.approved_by or not self.approved_at:
                raise UserError("Dispatch must be approved before sending.")

        new_status = self.env["ons.dispatch.status"].search([("code", "=", new_code)], limit=1)
        if not new_status:
            raise UserError("Status '%s' not found." % new_code)

        # Apply timestamp side effects
        vals = {"status_id": new_status.id}
        if new_code == "confirmed":
            vals["confirmed_at"] = fields.Datetime.now()
        elif new_code == "in_progress":
            vals["started_at"] = fields.Datetime.now()
        elif new_code == "completed":
            vals["completed_at"] = fields.Datetime.now()
        elif new_code == "cancelled":
            vals["cancelled_at"] = fields.Datetime.now()
            if kwargs.get("reason"):
                vals["cancellation_reason"] = kwargs["reason"]
            if kwargs.get("reason_id"):
                vals["cancellation_reason_id"] = kwargs["reason_id"]
        elif new_code == "voided":
            vals["voided_at"] = fields.Datetime.now()
            if kwargs.get("reason"):
                vals["void_reason"] = kwargs["reason"]

        self.write(vals)
        self._log_activity("status_change", "Status → %s" % new_code)
        return True

    # ── Quick actions ───────────────────────────────────────────────
    def action_send(self):
        self.ensure_one()
        if self.requires_approval and not self.approved_at:
            return self.action_change_status("pending_approval")
        return self.action_change_status("sent")

    def action_approve(self):
        self.ensure_one()
        self.write({
            "approved_by": self.env.uid,
            "approved_at": fields.Datetime.now(),
        })
        self._log_activity("approved", "Dispatch approved")
        return self.action_change_status("sent")

    def action_confirm(self):
        return self.action_change_status("confirmed")

    def action_start(self):
        return self.action_change_status("in_progress")

    def action_complete(self):
        return self.action_change_status("completed")

    def action_cancel(self, reason=None):
        return self.action_change_status("cancelled", reason=reason or "Cancelled by operator")

    def action_void(self, reason=None):
        return self.action_change_status("voided", reason=reason or "Voided by operator")

    # ── Checklist default population ────────────────────────────────
    def _create_default_checklist(self):
        """Create checklist items from active config."""
        configs = self.env["ons.dispatch.checklist.config"].search([("is_active", "=", True)])
        for cfg in configs:
            self.env["ons.dispatch.checklist.item"].create({
                "dispatch_id": self.id,
                "checklist_code": cfg.code,
                "name": cfg.name,
                "sequence": cfg.sequence,
                "is_required": cfg.is_required,
            })

    # ── Case pre-population ─────────────────────────────────────────
    @api.model
    def create_from_case(self, case):
        """Create a dispatch pre-populated from a service case."""
        partner = case.partner_id
        vals = {
            "case_id": case.id,
            "partner_id": partner.id,
            "title": "On-Site Computer Repair — %s" % (partner.city or "TBD"),
            "description": case.issue_description,
            "contact_first_name": (partner.name or "").split(" ")[0] if partner.name else "",
            "contact_last_name": " ".join((partner.name or "").split(" ")[1:]) if partner.name else "",
            "contact_phone": partner.phone or "",
            "street": partner.street or "",
            "street2": partner.street2 or "",
            "city": partner.city or "",
            "state_id": partner.state_id.id if partner.state_id else False,
            "zip": partner.zip or "",
            "country_id": partner.country_id.id if partner.country_id else False,
        }
        return self.create(vals)

    # ── Activity logging ────────────────────────────────────────────
    def _log_activity(self, event_type, description):
        self.env["ons.dispatch.activity.log"].create({
            "dispatch_id": self.id,
            "event_type": event_type,
            "description": description,
            "user_id": self.env.uid,
        })
