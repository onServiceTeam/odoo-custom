# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase


class TestWorkStatus(TransactionCase):
    """Tests for the work status feature on res.users."""

    def test_work_status_fields_exist(self):
        """work_status_emoji and work_status_text should exist on res.users."""
        self.assertIn("work_status_emoji", self.env["res.users"]._fields)
        self.assertIn("work_status_text", self.env["res.users"]._fields)

    def test_set_work_status(self):
        """Writing work_status_emoji/text should persist."""
        user = self.env.user
        user.write({"work_status_emoji": "🏠", "work_status_text": "Working remotely"})
        self.assertEqual(user.work_status_emoji, "🏠")
        self.assertEqual(user.work_status_text, "Working remotely")

    def test_manual_im_status_stripped(self):
        """manual_im_status should be silently dropped from write vals."""
        user = self.env.user
        user.write({"manual_im_status": "away", "work_status_text": "hello"})
        self.assertEqual(user.work_status_text, "hello")
