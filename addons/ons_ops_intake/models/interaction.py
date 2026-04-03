# -*- coding: utf-8 -*-
import datetime
import logging
import re

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


# ── Session-path → repair-status mapping (matches legacy) ──────
SESSION_PATH_REPAIR_MAP = {
    "no_session": "troubleshooting",
    "session_now": "online_session",
    "callback": "not_started",
    "onsite_queue": "requires_onsite",
}

# Terminal call statuses — trigger auto-completion
TERMINAL_CALL_STATUSES = {
    "completed", "transferred", "declined_sale", "wrong_number",
}


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
    agent_id = fields.Many2one("res.users", string="Phone Technician", tracking=True, index=True)
    assisting_agent_id = fields.Many2one("res.users", string="Assisting Technician")
    billing_agent_id = fields.Many2one("res.users", string="Verification & Billing Tech (VBT)")

    # ── Call details ────────────────────────────────────────────────
    queue_name = fields.Selection(
        [
            ("first_time_caller", "First Time Caller"),
            ("returning_caller", "Returning Caller"),
            ("questions_billing", "Questions & Billing"),
            ("callback", "Callback"),
        ],
        string="Inbound Queue",
    )
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
    call_status = fields.Selection(
        [
            ("in_progress", "In Progress"),
            ("completed", "Completed"),
            ("transferred", "Transferred"),
            ("set_for_callback", "Set for Callback"),
            ("repair_followup", "Repair Follow-up"),
            ("billing_question", "Billing Question"),
            ("hardware_issue", "Hardware Issue"),
            ("requires_onsite", "Requires Onsite"),
            ("declined_sale", "Declined Sale"),
            ("wrong_number", "Wrong Number"),
        ],
        default="in_progress",
        tracking=True,
    )

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
        [("low", "Low"), ("medium", "Medium"), ("high", "High"), ("urgent", "Urgent")],
        default="medium",
    )
    session_path = fields.Selection(
        [
            ("no_session", "Troubleshooting / No Online Session Yet"),
            ("session_now", "Online Session Started"),
            ("callback", "Callback Scheduled"),
            ("onsite_queue", "Sent to Onsite Queue"),
        ],
        default="no_session",
        required=True,
    )

    # ── Session / Callback / Onsite ─────────────────────────────────
    online_session_started = fields.Boolean(tracking=True)
    session_start_time = fields.Datetime()
    callback_requested = fields.Boolean(tracking=True)
    callback_time = fields.Datetime()
    callback_timezone = fields.Selection(
        [
            ("US/Eastern", "Eastern (ET)"),
            ("US/Central", "Central (CT)"),
            ("US/Mountain", "Mountain (MT)"),
            ("US/Pacific", "Pacific (PT)"),
            ("US/Hawaii", "Hawaii (HT)"),
            ("Asia/Manila", "Manila (PHT)"),
        ],
        default="US/Eastern",
    )
    repair_status = fields.Selection(
        [
            ("not_started", "Not Started"),
            ("troubleshooting", "Troubleshooting"),
            ("online_session", "Online Session In Progress"),
            ("pc_reset", "PC Reset In Progress"),
            ("other_work", "Other Work In Progress"),
            ("requires_onsite", "Requires Onsite"),
            ("ready_for_billing", "Ready for Billing"),
            ("ready_for_verification", "Ready for Verification"),
            ("completed", "Completed"),
            ("pending", "Pending"),
            ("waiting_for_parts", "Waiting for Parts"),
            ("on_hold", "On Hold"),
            ("cancelled", "Cancelled"),
            ("set_for_callback", "Set for Callback"),
            ("repair_followup", "Repair Follow-up"),
            ("not_applicable", "Not Applicable"),
        ],
        default="not_started",
        tracking=True,
    )

    # ── Address (for onsite dispatch) ───────────────────────────────
    address_street = fields.Char()
    address_street2 = fields.Char()
    address_city = fields.Char()
    address_state = fields.Char(string="State/Province")
    address_zip = fields.Char(string="ZIP")

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

    # ── Onchange: phone auto-lookup ─────────────────────────────────
    @api.onchange("customer_phone")
    def _onchange_customer_phone(self):
        """Auto-resolve partner when phone is entered (matches legacy auto-lookup)."""
        if not self.customer_phone or self.partner_id:
            return
        digits = re.sub(r"\D", "", self.customer_phone)
        if len(digits) < 7:
            return
        normalized = digits[-10:]
        Partner = self.env["res.partner"]
        candidates = Partner.search([("phone_sanitized", "like", normalized)], limit=10)
        matched = candidates.filtered(
            lambda p: re.sub(r"\D", "", p.phone_sanitized or "")[-10:] == normalized
        )
        if not matched:
            raw_candidates = Partner.search([
                ("phone", "like", normalized),
                ("phone_sanitized", "=", False),
            ], limit=10)
            matched = raw_candidates.filtered(
                lambda p: re.sub(r"\D", "", p.phone or "")[-10:] == normalized
            )
        if len(matched) == 1:
            self.partner_id = matched
            if not self.customer_name:
                self.customer_name = matched.name
            if not self.customer_email and matched.email:
                self.customer_email = matched.email
            self.caller_type = "returning"
        elif len(matched) > 1:
            return {"warning": {
                "title": "Multiple matches",
                "message": "%d customers match this phone number. Please select manually." % len(matched),
            }}

    # ── Onchange: session path → derived fields ─────────────────────
    @api.onchange("session_path")
    def _onchange_session_path(self):
        """Set repair_status, online_session_started, callback_requested based on path."""
        self.repair_status = SESSION_PATH_REPAIR_MAP.get(self.session_path, "not_started")
        self.online_session_started = self.session_path == "session_now"
        self.callback_requested = self.session_path == "callback"
        if self.session_path == "session_now" and not self.session_start_time:
            self.session_start_time = fields.Datetime.now()

    # ── Onchange: call_status → auto-complete ───────────────────────
    @api.onchange("call_status")
    def _onchange_call_status(self):
        """Terminal call statuses auto-set state to completed."""
        if self.call_status in TERMINAL_CALL_STATUSES and self.state != "completed":
            self.state = "completed"
        if self.call_status == "set_for_callback":
            self.callback_requested = True
            if not self.session_path or self.session_path == "no_session":
                self.session_path = "callback"

    # ── Sequence + post-create automation ───────────────────────────
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = self.env["ir.sequence"].next_by_code("ons.interaction") or "New"
            # Auto-classify if primary driver is set
            if vals.get("primary_driver_id") and vals.get("state", "new") == "new":
                vals["state"] = "classified"
        records = super().create(vals_list)
        for rec in records:
            rec._after_intake_create()
        return records

    def _after_intake_create(self):
        """Post-submit side effects — matches legacy POST /api/submissions flow."""
        # 1. Auto-resolve customer by phone if not already set
        if not self.partner_id and self.customer_phone:
            self.action_resolve_customer()

        # 2. Auto-fill agent to current user if not set
        if not self.agent_id:
            self.agent_id = self.env.uid

        # 3. Auto-fill VBT to current user if not set (matches legacy auto-default)
        if not self.billing_agent_id:
            self.billing_agent_id = self.env.uid

        # 3. Connector hook — subclasses / external modules can extend
        self._hook_after_intake()

    def _hook_after_intake(self):
        """Extension point for connectors (Discord, 3CX, etc.). Override in sub-modules."""
        pass

    # ── Cron: stale interaction cleanup ─────────────────────────────
    @api.model
    def _cron_mark_stale_interactions(self):
        """Auto-complete interactions stuck in new/classified for >24 hours."""
        cutoff = fields.Datetime.now() - datetime.timedelta(hours=24)
        stale = self.search([
            ("state", "in", ("new", "classified")),
            ("create_date", "<", cutoff),
        ])
        if stale:
            stale.write({"state": "completed"})
            _logger.info("Marked %d stale interactions as completed", len(stale))

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
        """Find existing partner by deterministic last-10-digit phone match, or create."""
        Partner = self.env["res.partner"]
        for rec in self:
            if rec.partner_id:
                continue
            phone = rec.customer_phone
            if not phone:
                continue
            # Normalize to last 10 digits (matches legacy RIGHT(regexp_replace(phone,'[^0-9]','','g'),10))
            digits = re.sub(r"\D", "", phone)
            if len(digits) < 7:
                continue
            normalized = digits[-10:]

            # Search phone_sanitized (E.164, most reliable) then verify exact last-10
            candidates = Partner.search([("phone_sanitized", "like", normalized)])
            matched = candidates.filtered(
                lambda p: re.sub(r"\D", "", p.phone_sanitized or "")[-10:] == normalized
            )

            # Fallback: check raw phone for partners without phone_sanitized
            if not matched:
                raw_candidates = Partner.search([
                    ("phone", "like", normalized),
                    ("phone_sanitized", "=", False),
                ])
                matched = raw_candidates.filtered(
                    lambda p: re.sub(r"\D", "", p.phone or "")[-10:] == normalized
                )

            if len(matched) == 1:
                rec.partner_id = matched
            elif len(matched) == 0:
                rec.partner_id = Partner.create({
                    "name": rec.customer_name or phone,
                    "phone": phone,
                    "email": rec.customer_email or False,
                    "customer_rank": 1,
                })
            else:
                # Multiple matches — refuse to auto-link, log for manual resolution
                rec.message_post(
                    body="Phone match ambiguous: %d partners match '%s'. "
                         "Please resolve manually." % (len(matched), normalized),
                    message_type="notification",
                    subtype_xmlid="mail.mt_note",
                )
