# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase


class TestDiscussIntake(TransactionCase):
    """Tests for the discuss.intake model."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.agent = cls.env.user
        # Create a channel for the agent
        cls.parent_channel = cls.env["discuss.channel"].create({
            "name": "Intake Agent Tickets",
            "channel_type": "channel",
        })
        cls.parent_channel.add_members(cls.agent.partner_id.ids)

    def test_intake_model_exists(self):
        """discuss.intake model should be registered."""
        self.assertIn("discuss.intake", self.env)

    def test_create_intake_creates_thread(self):
        """Creating an intake record should auto-create a customer thread."""
        intake = self.env["discuss.intake"].create({
            "name": "John Doe",
            "phone": "5551234567",
            "subject": "Need help",
            "channel_id": self.parent_channel.id,
        })
        self.assertTrue(intake.thread_id, "Thread should be created on intake creation")
        self.assertIn("John Doe", intake.thread_id.name)
        self.assertEqual(intake.thread_id.parent_channel_id, self.parent_channel)

    def test_phone_formatting(self):
        """Phone numbers should be formatted as XXX-XXX-XXXX."""
        intake = self.env["discuss.intake"].new({"name": "Test"})
        self.assertEqual(intake._format_phone("5551234567"), "555-123-4567")
        self.assertEqual(intake._format_phone("15551234567"), "555-123-4567")
        self.assertEqual(intake._format_phone(""), "")
        self.assertEqual(intake._format_phone(None), "")

    def test_intake_state_default(self):
        """Default state should be 'new'."""
        intake = self.env["discuss.intake"].create({
            "name": "Jane Doe",
            "channel_id": self.parent_channel.id,
        })
        self.assertEqual(intake.state, "new")

    def test_duplicate_phone_reuses_thread(self):
        """A second intake with the same phone should reuse the existing thread."""
        intake1 = self.env["discuss.intake"].create({
            "name": "John Doe",
            "phone": "5559876543",
            "channel_id": self.parent_channel.id,
        })
        intake2 = self.env["discuss.intake"].create({
            "name": "John Doe Callback",
            "phone": "5559876543",
            "channel_id": self.parent_channel.id,
        })
        self.assertEqual(
            intake1.thread_id.id,
            intake2.thread_id.id,
            "Second intake with same phone should reuse existing thread",
        )
