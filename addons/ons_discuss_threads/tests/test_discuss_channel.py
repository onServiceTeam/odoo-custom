# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase


class TestDiscussChannel(TransactionCase):
    """Tests for discuss.channel extensions in ons_discuss_threads."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.channel = cls.env["discuss.channel"].create({
            "name": "Test Channel",
            "channel_type": "channel",
        })

    def test_sequence_field_exists(self):
        """discuss.channel should have a sequence field."""
        self.assertIn("sequence", self.env["discuss.channel"]._fields)

    def test_sequence_default(self):
        """sequence should default to 10."""
        self.assertEqual(self.channel.sequence, 10)

    def test_sequence_writable(self):
        """sequence should be writable."""
        self.channel.sequence = 42
        self.assertEqual(self.channel.sequence, 42)

    def test_auto_cleanup_empty_group(self):
        """Auto-cleanup should delete empty group channels when enabled."""
        ICP = self.env["ir.config_parameter"].sudo()
        ICP.set_param("discuss_thread_admin.auto_cleanup_empty_groups", "True")

        group = self.env["discuss.channel"].create({
            "name": "Temp Group",
            "channel_type": "group",
        })
        partner = self.env.user.partner_id
        group.add_members(partner.ids)
        group_id = group.id

        # Leave the channel — should trigger auto-cleanup
        group._action_unfollow(partner=partner)

        # Channel should be deleted
        self.assertFalse(
            self.env["discuss.channel"].search([("id", "=", group_id)]),
            "Empty group channel should have been auto-deleted",
        )

    def test_auto_cleanup_disabled(self):
        """When auto-cleanup is off, empty groups should persist."""
        ICP = self.env["ir.config_parameter"].sudo()
        ICP.set_param("discuss_thread_admin.auto_cleanup_empty_groups", "False")

        group = self.env["discuss.channel"].create({
            "name": "Persistent Group",
            "channel_type": "group",
        })
        partner = self.env.user.partner_id
        group.add_members(partner.ids)
        group_id = group.id

        group._action_unfollow(partner=partner)

        self.assertTrue(
            self.env["discuss.channel"].search([("id", "=", group_id)]),
            "Group channel should persist when auto-cleanup is disabled",
        )
