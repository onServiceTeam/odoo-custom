# -*- coding: utf-8 -*-
import re

from odoo import api, fields, models


class Interaction(models.Model):
    _name = "ons.interaction"
    _description = "Customer Interaction"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "call_start desc, id desc"
    _rec_name = "name"

    # ── Identity ────────────────────────────────────────────────────
    name = fields.Char(
        string="Reference",
        readonly=True,
        default="New",
        copy=False,
        index=True,
    )
    interaction_type = fields.Selection(
        [
            ("phone", "Phone"),
            ("email", "Email"),
            ("sms", "SMS"),
            ("web_form", "Web Form"),
            ("callback", "Callback"),
        ],
        required=True,
        default="phone",
        tracking=True,
    )
    direction = fields.Selection(
        [("inbound", "Inbound"), ("outbound", "Outbound"), ("internal", "Internal")],
        default="inbound",
        tracking=True,
    )
    state = fields.Selection(
        [
            ("new", "New"),
            ("classified", "Classified"),
            ("assigned", "Assigned"),
            ("completed", "Completed"),
        ],
        default="new",
        required=True,
        tracking=True,
        index=True,
    )

    # ── Customer ────────────────────────────────────────────────────
    partner_id = fields.Many2one(
        "res.partner",
        string="Customer",
        tracking=True,
        index=True,
    )
    customer_name = fields.Char(string="Customer Name (raw)")
    customer_phone = fields.Char(string="Phone (raw)")
    customer_email = fields.Char(string="Email (raw)")
    caller_type = fields.Selection(
        [("new", "New Caller"), ("returning", "Returning Caller"), ("subscriber", "Subscriber")],
        tracking=True,
    )
    customer_type = fields.Selection(
        [("home", "Home User"), ("business", "Business User")],
    )

    # ── Agent attribution ───────────────────────────────────────────
    agent_id = fields.Many2one("res.users", string="Intake Agent", tracking=True, index=True)
    assisting_agent_id = fields.Many2one("res.users", string="Technician")
    billing_agent_id = fields.Many2one("res.users", string="Billing Agent")

    # ── Call details ────────────────────────────────────────────────
    queue_name = fields.Char(string="3CX Queue")
    call_start = fields.Datetime(tracking=True)
    call_end = fields.Datetime()
    call_duration = fields.Integer(string="Duration (s)", help="Total call duration in seconds")
    talk_duration = fields.Integer(string="Talk Time (s)")
    disposition = fields.Selection(
        [
            ("answered", "Answered"),
            ("missed", "Missed"),
            ("abandoned", "Abandoned"),
            ("voicemail", "Voicemail"),
            ("no_answer", "No Answer"),
        ],
        tracking=True,
    )
    has_recording = fields.Boolean()
    recording_url = fields.Char()

    # ── Classification ──────────────────────────────────────────────
    primary_driver_id = fields.Many2one(
        "ons.call.driver",
        string="Primary Driver",
        tracking=True,
        index=True,
    )
    secondary_driver_ids = fields.Many2many(
        "ons.call.driver",
        "ons_interaction_secondary_driver_rel",
        "interaction_id",
        "driver_id",
        string="Secondary Drivers",
    )
    ai_confidence = fields.Float(digits=(3, 2))
    ai_classification_raw = fields.Text(string="AI Raw Output")

    # ── Issue ───────────────────────────────────────────────────────
    issue_description = fields.Text(tracking=True)
    subject = fields.Char()
    urgency = fields.Selection(
        [("low", "Low"), ("medium", "Medium"), ("high", "High")],
        default="medium",
    )
    session_path = fields.Selection(
        [
            ("no_session", "No Session"),
            ("session_now", "Session Now"),
            ("callback", "Callback"),
            ("onsite_queue", "Onsite Queue"),
            ("session_scheduled", "Session Scheduled"),
            ("not_applicable", "N/A"),
        ],
        default="no_session",
    )

    # ── Transcript ──────────────────────────────────────────────────
    transcript = fields.Text()
    transcript_status = fields.Selection(
        [("pending", "Pending"), ("processing", "Processing"), ("completed", "Completed"), ("failed", "Failed")],
    )

    # ── Links ───────────────────────────────────────────────────────
    lead_id = fields.Many2one("crm.lead", string="CRM Lead", tracking=True, index=True)
    # case_id will be added by ons_ops_cases module
    threecx_cdr_id = fields.Char(string="3CX CDR ID", index=True, copy=False)
    legacy_discord_thread_id = fields.Char(string="Legacy Discord Thread")
    legacy_odoo_ticket_id = fields.Char(string="Legacy Odoo Ticket")

    # ── Computed ────────────────────────────────────────────────────
    duration_display = fields.Char(compute="_compute_duration_display")

    _threecx_cdr_unique = models.UniqueIndex("(threecx_cdr_id) WHERE threecx_cdr_id IS NOT NULL", "3CX CDR ID must be unique.")

    # ── Sequence ────────────────────────────────────────────────────
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = self.env["ir.sequence"].next_by_code("ons.interaction") or "New"
        return super().create(vals_list)

    # ── Computed fields ─────────────────────────────────────────────
    @api.depends("call_duration")
    def _compute_duration_display(self):
        for rec in self:
            if rec.call_duration:
                minutes, seconds = divmod(rec.call_duration, 60)
                rec.duration_display = f"{minutes}m {seconds:02d}s"
            else:
                rec.duration_display = ""

    # ── State transitions ───────────────────────────────────────────
    def action_classify(self):
        self.filtered(lambda r: r.state == "new").write({"state": "classified"})

    def action_assign(self):
        self.filtered(lambda r: r.state in ("new", "classified")).write({"state": "assigned"})

    def action_complete(self):
        self.filtered(lambda r: r.state != "completed").write({"state": "completed"})

    def action_reset_to_new(self):
        self.write({"state": "new"})

    # ── Customer resolution ─────────────────────────────────────────
    def action_resolve_customer(self):
        """Try to find an existing partner by phone, or create one."""
        for rec in self:
            if rec.partner_id:
                continue
            phone = rec.customer_phone
            if not phone:
                continue
            # Normalize to last 10 digits
            digits = re.sub(r"\D", "", phone)
            if len(digits) >= 10:
                digits = digits[-10:]
            partner = self.env["res.partner"].search(
                ["|", ("phone", "ilike", digits), ("phone_sanitized", "ilike", digits)],
                limit=1,
            )
            if partner:
                rec.partner_id = partner
            else:
                rec.partner_id = self.env["res.partner"].create({
                    "name": rec.customer_name or phone,
                    "phone": phone,
                    "email": rec.customer_email or False,
                    "customer_rank": 1,
                })
