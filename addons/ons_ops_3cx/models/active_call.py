# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ActiveCall(models.Model):
    _name = "ons.active.call"
    _description = "3CX Active Call (Ephemeral)"
    _order = "started_at desc, id desc"
    _rec_name = "display_name"

    # ── 3CX identifiers ────────────────────────────────────────────
    threecx_call_id = fields.Char(
        string="3CX Call ID",
        required=True,
        index=True,
    )

    _call_id_unique = models.UniqueIndex(
        "(threecx_call_id)",
        "Active call ID must be unique.",
    )

    # ── Parties ─────────────────────────────────────────────────────
    caller_number = fields.Char(string="Caller")
    callee_number = fields.Char(string="Callee")
    caller_name = fields.Char()
    callee_name = fields.Char()

    # ── Routing ─────────────────────────────────────────────────────
    direction = fields.Selection(
        [("inbound", "Inbound"), ("outbound", "Outbound"), ("internal", "Internal")],
    )
    queue = fields.Char(string="Queue")
    agent_extension = fields.Char(string="Agent Extension")
    agent_id = fields.Many2one(
        "res.users",
        string="Agent",
        help="Resolved from extension via ons.user.extension.",
    )

    # ── Timing ──────────────────────────────────────────────────────
    started_at = fields.Datetime(string="Started", index=True)
    duration_seconds = fields.Integer(
        compute="_compute_duration",
    )

    # ── State ───────────────────────────────────────────────────────
    call_state = fields.Selection(
        [
            ("ringing", "Ringing"),
            ("answered", "Answered"),
            ("on_hold", "On Hold"),
            ("transferring", "Transferring"),
        ],
        default="ringing",
    )

    # ── Display ─────────────────────────────────────────────────────
    display_name = fields.Char(compute="_compute_display_name")

    @api.depends("caller_number", "caller_name", "direction")
    def _compute_display_name(self):
        for rec in self:
            name = rec.caller_name or rec.caller_number or "Unknown"
            direction = (rec.direction or "inbound").capitalize()
            rec.display_name = "%s — %s" % (direction, name)

    @api.depends("started_at")
    def _compute_duration(self):
        now = fields.Datetime.now()
        for rec in self:
            if rec.started_at:
                delta = now - rec.started_at
                rec.duration_seconds = int(delta.total_seconds())
            else:
                rec.duration_seconds = 0

    # ── Sync / cleanup ──────────────────────────────────────────────
    @api.model
    def _cron_sync_active_calls(self):
        """Placeholder for 3CX active call sync.
        No-ops when 3CX credentials are not configured."""
        host = self.env["ir.config_parameter"].sudo().get_param("ons_ops_3cx.host", "")
        if not host:
            return
        # Future: poll /activecalls, upsert records, purge stale

    @api.model
    def _cron_cleanup_stale(self):
        """Remove active call records older than 1 hour."""
        cutoff = fields.Datetime.subtract(fields.Datetime.now(), hours=1)
        stale = self.search([("started_at", "<", cutoff)])
        stale.unlink()
