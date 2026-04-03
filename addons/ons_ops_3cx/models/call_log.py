# -*- coding: utf-8 -*-
import re

from odoo import api, fields, models
from odoo.exceptions import UserError

# 3CX queue name → interaction queue_name Selection key
QUEUE_NAME_MAP = {
    "First Time Caller": "first_time_caller",
    "Returning Caller": "returning_caller",
    "Questions & Billing": "questions_billing",
    "Callback": "callback",
}


class CallLog(models.Model):
    _name = "ons.call.log"
    _description = "3CX Call Detail Record"
    _order = "call_start desc, id desc"
    _rec_name = "display_name"

    # ── 3CX identifiers ────────────────────────────────────────────
    cdr_primary_id = fields.Char(
        string="CDR Primary ID",
        index=True,
        copy=False,
        help="Unique 3CX CDR ID from XAPI recordings endpoint.",
    )
    threecx_call_id = fields.Char(
        string="3CX Call ID",
        index=True,
        help="3CX internal call identifier (e.g. 3cx-12345).",
    )

    _cdr_unique = models.UniqueIndex(
        "(cdr_primary_id) WHERE cdr_primary_id IS NOT NULL",
        "CDR Primary ID must be unique.",
    )

    # ── Parties ─────────────────────────────────────────────────────
    caller_number = fields.Char(
        string="Caller Number",
        help="Raw caller number from 3CX (may include country prefix).",
    )
    callee_number = fields.Char(
        string="Callee Number",
        help="Raw callee number from 3CX.",
    )
    customer_number = fields.Char(
        string="Customer Number",
        index=True,
        help="Normalized 10-digit customer phone number.",
    )
    partner_id = fields.Many2one(
        "res.partner",
        string="Customer",
        index=True,
        help="Auto-resolved partner from phone number. Empty if ambiguous or new.",
    )
    match_status = fields.Selection(
        [
            ("matched", "Matched"),
            ("new_caller", "New Caller"),
            ("ambiguous", "Ambiguous"),
            ("manual", "Manual Match"),
        ],
        string="Match Status",
        default="new_caller",
        help="Partner resolution outcome.",
    )

    # ── Routing ─────────────────────────────────────────────────────
    direction = fields.Selection(
        [
            ("inbound", "Inbound"),
            ("outbound", "Outbound"),
            ("internal", "Internal"),
        ],
        index=True,
    )
    queue_name = fields.Char(
        string="Queue",
        index=True,
        help="3CX queue (e.g. 'First Time Caller', 'Returning Caller').",
    )
    agent_extension = fields.Char(
        string="Agent Extension",
        index=True,
        help="3CX extension of the agent who handled the call.",
    )
    agent_id = fields.Many2one(
        "res.users",
        string="Agent",
        index=True,
        help="Resolved from agent_extension via ons.user.extension.",
    )

    # ── Timing ──────────────────────────────────────────────────────
    call_start = fields.Datetime(string="Call Start", index=True)
    call_end = fields.Datetime(string="Call End")
    call_duration = fields.Integer(string="Duration (s)", help="Total seconds")
    ring_duration = fields.Integer(string="Ring Time (s)")
    hold_duration = fields.Integer(string="Hold Time (s)")
    talk_duration = fields.Integer(string="Talk Time (s)")
    wait_duration = fields.Integer(string="Wait Time (s)")

    # ── Outcome ─────────────────────────────────────────────────────
    disposition = fields.Selection(
        [
            ("answered", "Answered"),
            ("missed", "Missed"),
            ("abandoned", "Abandoned"),
            ("transferred", "Transferred"),
            ("voicemail", "Voicemail"),
            ("no_answer", "No Answer"),
        ],
        index=True,
    )

    # ── Recording ───────────────────────────────────────────────────
    has_recording = fields.Boolean(default=False)
    recording_url = fields.Char(string="Recording URL")

    # ── Classification (from legacy/sync) ───────────────────────────
    caller_type = fields.Selection(
        [
            ("new", "New"),
            ("returning", "Returning"),
            ("subscriber", "Subscriber"),
        ],
    )
    customer_type = fields.Selection(
        [("home", "Home"), ("business", "Business")],
    )

    # ── Links ───────────────────────────────────────────────────────
    interaction_id = fields.Many2one(
        "ons.interaction",
        string="Interaction",
        help="The intake interaction created from this call.",
    )

    # ── Display ─────────────────────────────────────────────────────
    display_name = fields.Char(compute="_compute_display_name", store=True)
    duration_display = fields.Char(compute="_compute_duration_display")

    # ── Metadata ────────────────────────────────────────────────────
    metadata = fields.Json(
        string="3CX Metadata",
        help="Raw metadata from 3CX XAPI (threecx_id, call_type, DIDs, etc.).",
    )

    # ── Computed ────────────────────────────────────────────────────
    @api.depends("caller_number", "call_start", "direction")
    def _compute_display_name(self):
        for rec in self:
            parts = []
            if rec.direction:
                parts.append(rec.direction.upper()[:2])
            if rec.caller_number:
                parts.append(rec.caller_number[-10:] if len(rec.caller_number or "") > 10 else rec.caller_number)
            if rec.call_start:
                parts.append(rec.call_start.strftime("%m/%d %H:%M"))
            rec.display_name = " — ".join(parts) if parts else "Call Log"

    @api.depends("call_duration")
    def _compute_duration_display(self):
        for rec in self:
            if rec.call_duration:
                m, s = divmod(rec.call_duration, 60)
                rec.duration_display = "%d:%02d" % (m, s)
            else:
                rec.duration_display = "0:00"

    # ── Phone normalization ─────────────────────────────────────────
    @staticmethod
    def _normalize_phone(raw):
        """Normalize phone to last 10 digits."""
        if not raw:
            return False
        digits = re.sub(r"\D", "", raw)
        return digits[-10:] if len(digits) >= 10 else digits

    # ── Partner resolution ──────────────────────────────────────────
    def _resolve_partner(self):
        """Resolve partner from customer_number. Sets partner_id and match_status."""
        for rec in self:
            if not rec.customer_number:
                rec.match_status = "new_caller"
                continue
            partners = self.env["res.partner"].search([
                ("phone", "like", rec.customer_number),
            ])
            if len(partners) == 1:
                rec.partner_id = partners
                rec.match_status = "matched"
            elif len(partners) > 1:
                rec.match_status = "ambiguous"
            else:
                rec.match_status = "new_caller"

    # ── Actions ─────────────────────────────────────────────────────
    def action_create_interaction(self):
        """Create an ons.interaction pre-populated from this CDR."""
        self.ensure_one()
        if self.interaction_id:
            raise UserError("This call already has an interaction: %s" % self.interaction_id.name)

        vals = {
            "interaction_type": "phone",
            "direction": self.direction or "inbound",
            "threecx_cdr_id": self.cdr_primary_id,
            "call_log_id": self.id,
            "customer_phone": self.customer_number or self.caller_number,
            "call_start": self.call_start,
            "call_end": self.call_end,
            "call_duration": self.call_duration,
            "talk_duration": self.talk_duration,
            "queue_name": QUEUE_NAME_MAP.get(self.queue_name, False),
            "disposition": self.disposition if self.disposition in ("answered", "missed", "abandoned", "voicemail", "no_answer") else False,
            "has_recording": self.has_recording,
            "recording_url": self.recording_url,
            "caller_type": self.caller_type if self.caller_type in ("new", "returning", "subscriber") else False,
            "customer_type": self.customer_type,
        }
        if self.partner_id:
            vals["partner_id"] = self.partner_id.id
            vals["customer_name"] = self.partner_id.name
        if self.agent_id:
            vals["agent_id"] = self.agent_id.id

        interaction = self.env["ons.interaction"].create(vals)
        self.interaction_id = interaction
        return {
            "type": "ir.actions.act_window",
            "res_model": "ons.interaction",
            "res_id": interaction.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_resolve_partner(self):
        """Manually trigger partner resolution."""
        self._resolve_partner()

    # ── Sync helpers (called by cron or external scripts) ───────────
    @api.model
    def _cron_sync_from_3cx(self):
        """Placeholder for 3CX CDR sync. The actual XAPI call logic
        will be implemented when 3CX credentials are configured.
        This cron is safe to enable — it no-ops when config is missing."""
        host = self.env["ir.config_parameter"].sudo().get_param("ons_ops_3cx.host", "")
        if not host:
            return
        # Future: call 3CX XAPI /recordings, normalize, create/update records
        # See docs/architecture/62_realtime_vs_sync_boundary.md

    @api.model
    def _normalize_and_resolve_batch(self, records):
        """Normalize phone numbers and resolve partners for a batch."""
        for rec in records:
            rec.customer_number = self._normalize_phone(rec.caller_number)
        records._resolve_partner()

    @api.model
    def create(self, vals_list):
        """Auto-normalize customer_number on create."""
        if isinstance(vals_list, dict):
            vals_list = [vals_list]
        for vals in vals_list:
            if vals.get("caller_number") and not vals.get("customer_number"):
                vals["customer_number"] = self._normalize_phone(vals["caller_number"])
        records = super().create(vals_list)
        records._resolve_partner()
        return records
