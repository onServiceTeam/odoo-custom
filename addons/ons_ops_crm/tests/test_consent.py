# -*- coding: utf-8 -*-
from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


class TestConsentModel(TransactionCase):
    """Tests for ons.contact.consent model."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({
            "name": "Consent Test Customer",
            "phone": "5559998877",
        })

    def _create_consent(self, **kw):
        vals = {
            "partner_id": self.partner.id,
            "channel": "email",
            "scope": "marketing",
            "capture_source": "phone_call",
        }
        vals.update(kw)
        return self.env["ons.contact.consent"].create(vals)

    def test_consent_created_pending(self):
        """New consent should default to pending status."""
        consent = self._create_consent()
        self.assertEqual(consent.status, "pending")

    def test_opt_in_transition(self):
        """action_opt_in should move pending → opted_in and set timestamp."""
        consent = self._create_consent()
        consent.action_opt_in()
        self.assertEqual(consent.status, "opted_in")
        self.assertTrue(consent.opted_in_at)

    def test_double_opt_in(self):
        """action_confirm should move opted_in → double_opted_in."""
        consent = self._create_consent()
        consent.action_opt_in()
        consent.action_confirm()
        self.assertEqual(consent.status, "double_opted_in")
        self.assertTrue(consent.confirmed_at)

    def test_opt_out_from_opted_in(self):
        """action_opt_out from opted_in should set opted_out."""
        consent = self._create_consent()
        consent.action_opt_in()
        consent.action_opt_out()
        self.assertEqual(consent.status, "opted_out")
        self.assertTrue(consent.opted_out_at)

    def test_opt_out_from_pending(self):
        """action_opt_out from pending should set opted_out."""
        consent = self._create_consent()
        consent.action_opt_out()
        self.assertEqual(consent.status, "opted_out")

    def test_opt_out_is_terminal(self):
        """Cannot transition from opted_out to any other status."""
        consent = self._create_consent()
        consent.action_opt_out()
        with self.assertRaises(UserError):
            consent.action_opt_in()

    def test_opt_in_from_non_pending_rejected(self):
        """Cannot opt_in from opted_in or double_opted_in."""
        consent = self._create_consent()
        consent.action_opt_in()
        with self.assertRaises(UserError):
            consent.action_opt_in()

    def test_confirm_from_non_opted_in_rejected(self):
        """Cannot confirm from pending (must opt in first)."""
        consent = self._create_consent()
        with self.assertRaises(UserError):
            consent.action_confirm()

    def test_write_once_timestamps(self):
        """Timestamp fields should be write-once."""
        consent = self._create_consent()
        consent.action_opt_in()  # sets opted_in_at
        with self.assertRaises(UserError):
            consent.write({"opted_in_at": consent.opted_in_at})

    def test_unique_active_constraint(self):
        """Only one active consent per (partner, channel, scope)."""
        self._create_consent(channel="sms", scope="operational")
        with self.assertRaises(Exception):
            self._create_consent(channel="sms", scope="operational")

    def test_different_channel_scope_allowed(self):
        """Different channel+scope combos should be allowed."""
        c1 = self._create_consent(channel="email", scope="marketing")
        c2 = self._create_consent(channel="sms", scope="operational")
        c3 = self._create_consent(channel="email", scope="callback")
        self.assertTrue(c1.id != c2.id != c3.id)

    def test_has_consent_helper(self):
        """partner.has_consent() should check active opted-in records."""
        self.assertFalse(self.partner.has_consent("email", "marketing"))
        consent = self._create_consent()
        self.assertFalse(self.partner.has_consent("email", "marketing"))  # still pending
        consent.action_opt_in()
        self.assertTrue(self.partner.has_consent("email", "marketing"))

    def test_has_consent_double_opted(self):
        """Double opted-in should also satisfy has_consent check."""
        consent = self._create_consent()
        consent.action_opt_in()
        consent.action_confirm()
        self.assertTrue(self.partner.has_consent("email", "marketing"))

    def test_has_consent_false_after_opt_out(self):
        """has_consent should return False after opt-out."""
        consent = self._create_consent()
        consent.action_opt_in()
        self.assertTrue(self.partner.has_consent("email", "marketing"))
        consent.action_opt_out()
        self.assertFalse(self.partner.has_consent("email", "marketing"))

    def test_consent_count_on_partner(self):
        """consent_count should reflect linked consent records."""
        self.assertEqual(self.partner.consent_count, 0)
        self._create_consent(channel="email", scope="marketing")
        self._create_consent(channel="sms", scope="operational")
        self.partner.invalidate_recordset()
        self.assertEqual(self.partner.consent_count, 2)

    def test_display_name_computed(self):
        """display_name should show channel / scope — status."""
        consent = self._create_consent()
        self.assertIn("Email", consent.display_name)
        self.assertIn("Marketing", consent.display_name)
        self.assertIn("Pending", consent.display_name)

    def test_revoke_archives_record(self):
        """action_revoke should set revoked status and archive."""
        consent = self._create_consent()
        consent.action_opt_in()
        consent.action_revoke()
        self.assertEqual(consent.status, "revoked")
        self.assertFalse(consent.active)
        self.assertTrue(consent.revoked_at)

    def test_consent_never_deleted(self):
        """Consent should not be unlinked by agents (no unlink perm)."""
        # Agents have perm_unlink=0 in security CSV.
        # We verify the access CSV was loaded correctly via xmlid check.
        acl = self.env.ref(
            "ons_ops_crm.access_consent_agent",
            raise_if_not_found=False,
        )
        self.assertTrue(acl, "Agent ACL for consent not found")
        self.assertFalse(acl.perm_unlink, "Agents should NOT have unlink permission")
