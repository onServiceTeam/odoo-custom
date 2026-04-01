# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase


class TestVoiceChannel(TransactionCase):
    """Tests for voice channel behavior."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.channel = cls.env["discuss.channel"].create({
            "name": "Voice Room",
            "channel_type": "channel",
            "is_voice_channel": True,
        })
        cls.normal_channel = cls.env["discuss.channel"].create({
            "name": "Normal Channel",
            "channel_type": "channel",
            "is_voice_channel": False,
        })

    def test_is_voice_channel_field(self):
        """is_voice_channel field should exist and default to False."""
        self.assertIn("is_voice_channel", self.env["discuss.channel"]._fields)
        ch = self.env["discuss.channel"].create({
            "name": "Default Channel",
            "channel_type": "channel",
        })
        self.assertFalse(ch.is_voice_channel)

    def test_voice_channel_flag(self):
        """Setting is_voice_channel=True should persist."""
        self.assertTrue(self.channel.is_voice_channel)
        self.assertFalse(self.normal_channel.is_voice_channel)

    def test_voice_channel_toggle(self):
        """is_voice_channel should be toggleable."""
        self.channel.is_voice_channel = False
        self.assertFalse(self.channel.is_voice_channel)
        self.channel.is_voice_channel = True
        self.assertTrue(self.channel.is_voice_channel)

    def test_message_post_skips_call_notification_in_voice(self):
        """message_post should skip call notifications for voice channels."""
        body = '<div data-oe-type="call">Someone started a call</div>'
        # Set context flag like RTC session create would
        channel = self.channel.with_context(
            _voice_skip_call_notification={self.channel.id}
        )
        msg = channel.message_post(
            message_type="notification",
            body=body,
        )
        # Should return empty recordset (message was skipped)
        self.assertFalse(msg, "Call notification should be suppressed for voice channels")

    def test_message_post_normal_channel_not_skipped(self):
        """Normal channels should still get call notifications."""
        body = '<div data-oe-type="call">Someone started a call</div>'
        msg = self.normal_channel.message_post(
            message_type="notification",
            body=body,
        )
        self.assertTrue(msg, "Normal channel should get the call notification")
