# -*- coding: utf-8 -*-
import logging
import re

from markupsafe import Markup

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


class DiscussIntake(models.Model):
    """Customer intake record.

    When created, automatically creates a sub-channel (thread) under
    the assigned user's Discuss channel, named after the customer +
    phone number — mirroring the OnService Discord workflow.
    """

    _name = "discuss.intake"
    _description = "Customer Intake"
    _order = "create_date desc"

    name = fields.Char(
        "Customer Name",
        required=True,
    )
    phone = fields.Char(
        "Phone Number",
    )
    subject = fields.Char(
        "Subject",
    )
    description = fields.Text(
        "Issue Description",
    )
    agent_id = fields.Many2one(
        "res.users",
        string="Assigned Agent",
        default=lambda self: self.env.user,
        required=True,
    )
    channel_id = fields.Many2one(
        "discuss.channel",
        string="Agent's Channel",
        help="The parent channel under which the customer thread is created.",
    )
    thread_id = fields.Many2one(
        "discuss.channel",
        string="Customer Thread",
        help="The sub-channel created for this customer.",
        readonly=True,
    )
    state = fields.Selection(
        [
            ("new", "New"),
            ("in_progress", "In Progress"),
            ("completed", "Completed"),
        ],
        default="new",
        string="Status",
    )
    caller_type = fields.Selection(
        [
            ("new", "New Customer"),
            ("existing", "Existing Customer"),
            ("callback", "Callback"),
        ],
        string="Caller Type",
    )
    call_driver = fields.Char(
        "Primary Driver",
    )

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records:
            record._create_customer_thread()
        return records

    def _format_phone(self, phone):
        """Format phone for display: 1234567890 → 123-456-7890"""
        if not phone:
            return ""
        digits = re.sub(r"\D", "", phone)
        if len(digits) == 10:
            return f"{digits[:3]}-{digits[3:6]}-{digits[6:]}"
        if len(digits) == 11 and digits[0] == "1":
            return f"{digits[1:4]}-{digits[4:7]}-{digits[7:]}"
        return phone

    def _build_thread_name(self):
        """Build thread name like Discord: 'Customer Name - 123-456-7890'"""
        parts = [self.name or "Unknown Customer"]
        formatted_phone = self._format_phone(self.phone)
        if formatted_phone:
            parts.append(f"- {formatted_phone}")
        return " ".join(parts)[:100]  # Discord thread name limit

    def _find_agent_channel(self):
        """Find the agent's parent channel.

        Priority:
        1. Explicitly set channel_id on the record
        2. A channel whose name contains the agent's name + "Tickets"
        3. Any channel where the agent is a member (non-chat, non-group)
        """
        if self.channel_id:
            return self.channel_id

        agent = self.agent_id
        Channel = self.env["discuss.channel"].sudo()

        # Try to find by convention: "Agent's Tickets"
        agent_name = agent.partner_id.name or agent.name
        candidates = Channel.search(
            [
                ("channel_type", "=", "channel"),
                ("parent_channel_id", "=", False),
                ("name", "ilike", agent_name),
            ],
            limit=5,
        )
        if candidates:
            return candidates[0]

        # Fallback: any channel the agent is a member of
        members = self.env["discuss.channel.member"].sudo().search(
            [("partner_id", "=", agent.partner_id.id)],
            limit=20,
        )
        for member in members:
            ch = member.channel_id
            if ch.channel_type == "channel" and not ch.parent_channel_id:
                return ch

        return Channel  # empty recordset

    def _build_initial_message(self):
        """Build the initial message posted in the customer thread."""
        lines = []

        # @mention the agent
        agent_name = self.agent_id.partner_id.name or self.agent_id.name
        lines.append(f"<strong>New Customer Intake</strong> — assigned to {agent_name}")
        lines.append("")

        if self.subject:
            lines.append(f"<strong>Subject:</strong> {self.subject}")
        lines.append(f"<strong>Customer:</strong> {self.name}")
        if self.phone:
            lines.append(f"<strong>Phone:</strong> {self._format_phone(self.phone)}")
        if self.caller_type:
            labels = dict(self._fields["caller_type"].selection)
            lines.append(f"<strong>Caller Type:</strong> {labels.get(self.caller_type, self.caller_type)}")
        if self.call_driver:
            lines.append(f"<strong>Primary Driver:</strong> {self.call_driver}")
        if self.description:
            lines.append(f"<br/><strong>Issue:</strong><br/>{self.description[:500]}")

        return Markup("<br/>".join(lines))

    def _create_customer_thread(self):
        """Create a sub-channel under the agent's channel for this customer."""
        self.ensure_one()

        parent_channel = self._find_agent_channel()
        if not parent_channel:
            _logger.warning(
                "Intake %s: No parent channel found for agent %s",
                self.id,
                self.agent_id.name,
            )
            return

        # Store the parent channel
        self.channel_id = parent_channel.id

        # Check for existing thread (dedup by phone + parent channel)
        if self.phone:
            existing = self.env["discuss.channel"].sudo().search(
                [
                    ("parent_channel_id", "=", parent_channel.id),
                    ("name", "=like", f"% - {self._format_phone(self.phone)}"),
                ],
                limit=1,
            )
            if existing:
                self.thread_id = existing.id
                # Post update to existing thread
                body = Markup(
                    "<p><strong>Update from intake</strong></p>"
                    "<p><strong>Subject:</strong> %s</p>"
                    "<p><strong>Description:</strong> %s</p>"
                ) % (
                    self.subject or "(none)",
                    (self.description or "(none)")[:300],
                )
                existing.message_post(
                    body=body,
                    subtype_xmlid="mail.mt_comment",
                    author_id=self.agent_id.partner_id.id,
                )
                _logger.info(
                    "Intake %s: posted update to existing thread %s",
                    self.id,
                    existing.id,
                )
                return

        # Create new sub-channel (thread)
        thread_name = self._build_thread_name()
        thread = (
            self.env["discuss.channel"]
            .sudo()
            .create(
                {
                    "name": thread_name,
                    "channel_type": "channel",
                    "parent_channel_id": parent_channel.id,
                    "description": f"Customer intake: {self.name}",
                }
            )
        )

        # Add the agent as a member
        thread.add_members(self.agent_id.partner_id.ids)

        self.thread_id = thread.id

        # Post the initial message
        body = self._build_initial_message()
        thread.message_post(
            body=body,
            subtype_xmlid="mail.mt_comment",
            author_id=self.agent_id.partner_id.id,
        )

        _logger.info(
            "Intake %s: created thread '%s' (id=%s) under channel '%s'",
            self.id,
            thread_name,
            thread.id,
            parent_channel.name,
        )
