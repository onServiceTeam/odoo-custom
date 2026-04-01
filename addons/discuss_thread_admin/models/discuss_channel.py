# -*- coding: utf-8 -*-
import logging

from markupsafe import Markup

from odoo import _, fields, models

_logger = logging.getLogger(__name__)


class DiscussChannel(models.Model):
    _inherit = "discuss.channel"

    is_voice_channel = fields.Boolean(
        "Voice Channel",
        default=False,
        help="When enabled, users auto-join voice when entering this channel.",
    )

    sequence = fields.Integer(
        "Sequence",
        default=10,
        help="Order in the sidebar. Lower = higher in the list.",
    )

    def _to_store_defaults(self, target):
        """Extend store data to include voice channel flag and sequence."""
        res = super()._to_store_defaults(target)
        res.append("is_voice_channel")
        res.append("sequence")
        return res

    def message_post(self, *, message_type="notification", body="", **kwargs):
        """Skip 'started a call' notifications for voice channels.

        The RTC session create() sets a context flag when a voice channel
        gets its first session.  We intercept the notification here so it
        is never created (avoiding a bus‑notification race).
        """
        skip_ids = self.env.context.get("_voice_skip_call_notification")
        if (
            skip_ids
            and self.id in skip_ids
            and message_type == "notification"
            and 'data-oe-type="call"' in str(body)
        ):
            return self.env["mail.message"]
        return super().message_post(message_type=message_type, body=body, **kwargs)

    def _action_unfollow(self, partner=None, guest=None, post_leave_message=True):
        """Override to auto-cleanup empty group channels after the last member leaves."""
        res = super()._action_unfollow(
            partner=partner, guest=guest, post_leave_message=post_leave_message
        )
        # After the standard unfollow, check if the channel is now empty
        auto_cleanup = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("discuss_thread_admin.auto_cleanup_empty_groups", "True")
        )
        if auto_cleanup != "True":
            return res
        for channel in self:
            if channel.channel_type == "group" and channel.member_count == 0:
                _logger.info(
                    "Auto-cleanup: deleting empty group channel %s (id=%s)",
                    channel.name or "(unnamed)",
                    channel.id,
                )
                # sudo: discuss.channel — cleanup of orphaned channels
                channel.sudo().unlink()
        return res
