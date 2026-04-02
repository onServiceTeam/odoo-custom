# -*- coding: utf-8 -*-
from odoo import api, fields, models


class AgentStatus(models.Model):
    _name = "ons.agent.status"
    _description = "3CX Agent Status"
    _order = "agent_name, id"
    _rec_name = "display_name"

    # ── Core ────────────────────────────────────────────────────────
    extension = fields.Char(
        required=True,
        index=True,
    )
    user_id = fields.Many2one(
        "res.users",
        string="User",
        index=True,
        help="Resolved from ons.user.extension.",
    )
    agent_name = fields.Char(string="Agent Name")
    status = fields.Selection(
        [
            ("available", "Available"),
            ("on_call", "On Call"),
            ("dnd", "Do Not Disturb"),
            ("away", "Away"),
            ("lunch", "Lunch"),
            ("offline", "Offline"),
            ("not_registered", "Not Registered"),
        ],
        default="offline",
        index=True,
    )
    reason = fields.Char(string="Status Reason")
    since = fields.Datetime(string="Since", help="When this status started")

    # ── Unique per extension ────────────────────────────────────────
    _extension_unique = models.UniqueIndex(
        "(extension)",
        "One status record per extension.",
    )

    # ── Display ─────────────────────────────────────────────────────
    display_name = fields.Char(compute="_compute_display_name")

    @api.depends("agent_name", "extension", "status")
    def _compute_display_name(self):
        for rec in self:
            name = rec.agent_name or ("Ext %s" % rec.extension)
            state = dict(self._fields["status"].selection).get(rec.status, "")
            rec.display_name = "%s — %s" % (name, state)

    # ── Sync ────────────────────────────────────────────────────────
    @api.model
    def _cron_sync_agent_status(self):
        """Placeholder for 3CX agent status sync.
        No-ops when 3CX credentials are not configured."""
        host = self.env["ir.config_parameter"].sudo().get_param("ons_ops_3cx.host", "")
        if not host:
            return
        # Future: poll /users, resolve extension→user, upsert status
