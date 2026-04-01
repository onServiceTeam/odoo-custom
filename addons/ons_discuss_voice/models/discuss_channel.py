# -*- coding: utf-8 -*-
from markupsafe import Markup

from odoo import _, fields, models


class DiscussChannel(models.Model):
    _inherit = "discuss.channel"

    is_voice_channel = fields.Boolean(
        "Voice Channel",
        default=False,
        help="When enabled, users auto-join voice when entering this channel.",
    )

    def _to_store_defaults(self, target):
        """Extend store data to include voice channel flag."""
        res = super()._to_store_defaults(target)
        res.append("is_voice_channel")
        return res

    def message_post(self, *, message_type="notification", body="", **kwargs):
        """Skip 'started a call' notifications for voice channels.

        The RTC session create() sets a context flag when a voice channel
        gets its first session.  We intercept the notification here so it
        is never created (avoiding a bus-notification race).
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
