# -*- coding: utf-8 -*-

from odoo import api, models


class DiscussChannelRtcSession(models.Model):
    _inherit = "discuss.channel.rtc.session"

    @api.model_create_multi
    def create(self, vals_list):
        """Override to suppress 'started a call' notification for voice channels.

        Stock Odoo posts a notification message (via message_post) when the
        first RTC session is created on a channel.  For voice channels the
        call is always-on, so this notification is unwanted noise.

        We set a context flag *before* calling super so that our
        message_post override on discuss.channel can silently skip the
        call notification for voice channels.
        """
        voice_channel_ids = set()
        for vals in vals_list:
            member = self.env["discuss.channel.member"].browse(
                vals.get("channel_member_id")
            )
            channel = member.channel_id
            if channel.is_voice_channel and len(channel.rtc_session_ids) == 0:
                voice_channel_ids.add(channel.id)

        if voice_channel_ids:
            self = self.with_context(
                _voice_skip_call_notification=voice_channel_ids
            )

        rtc_sessions = super().create(vals_list)

        # Clean up orphaned call_history records that stock code created
        # with a NULL start_call_message_id (because our message_post
        # override returned an empty recordset for voice channels).
        if voice_channel_ids:
            orphans = (
                self.env["discuss.call.history"]
                .sudo()
                .search(
                    [
                        ("channel_id", "in", list(voice_channel_ids)),
                        ("start_call_message_id", "=", False),
                    ]
                )
            )
            if orphans:
                orphans.unlink()

        return rtc_sessions

