# -*- coding: utf-8 -*-
import logging

from odoo import _, fields, models

_logger = logging.getLogger(__name__)


class DiscussChannel(models.Model):
    _inherit = "discuss.channel"

    sequence = fields.Integer(
        "Sequence",
        default=10,
        help="Order in the sidebar. Lower = higher in the list.",
    )

    def _to_store_defaults(self, target):
        """Extend store data to include sequence for drag-and-drop reorder."""
        res = super()._to_store_defaults(target)
        res.append("sequence")
        return res

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
