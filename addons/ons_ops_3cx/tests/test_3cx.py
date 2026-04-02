# -*- coding: utf-8 -*-
from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class Test3CX(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))

        # Test user + extension
        cls.test_user = cls.env["res.users"].create({
            "name": "Agent Smith",
            "login": "agent_smith_3cx",
            "email": "smith@test.com",
        })

        cls.extension = cls.env["ons.user.extension"].create({
            "extension": "1050",
            "user_id": cls.test_user.id,
        })

        # Test partner with known phone
        cls.partner = cls.env["res.partner"].create({
            "name": "John Doe 3CX",
            "phone": "5125551234",
        })

    # ── User Extension Tests ────────────────────────────────────────
    def test_extension_creation(self):
        self.assertEqual(self.extension.extension, "1050")
        self.assertEqual(self.extension.user_id, self.test_user)
        self.assertTrue(self.extension.is_active)

    def test_extension_display_name(self):
        self.assertIn("1050", self.extension.display_name)
        self.assertIn("Agent Smith", self.extension.display_name)

    def test_extension_unique_constraint(self):
        """Active extensions must be unique."""
        with self.assertRaises(Exception):
            self.env["ons.user.extension"].create({
                "extension": "1050",
                "user_id": self.test_user.id,
            })

    # ── Phone Normalization Tests ───────────────────────────────────
    def test_normalize_phone_10_digits(self):
        result = self.env["ons.call.log"]._normalize_phone("5125551234")
        self.assertEqual(result, "5125551234")

    def test_normalize_phone_with_country_code(self):
        result = self.env["ons.call.log"]._normalize_phone("+15125551234")
        self.assertEqual(result, "5125551234")

    def test_normalize_phone_with_formatting(self):
        result = self.env["ons.call.log"]._normalize_phone("(512) 555-1234")
        self.assertEqual(result, "5125551234")

    def test_normalize_phone_short_number(self):
        result = self.env["ons.call.log"]._normalize_phone("5551234")
        self.assertEqual(result, "5551234")

    def test_normalize_phone_empty(self):
        self.assertFalse(self.env["ons.call.log"]._normalize_phone(""))
        self.assertFalse(self.env["ons.call.log"]._normalize_phone(None))

    # ── Call Log Creation + Auto-Normalization ──────────────────────
    def test_call_log_creation_auto_normalize(self):
        log = self.env["ons.call.log"].create({
            "caller_number": "+15125551234",
            "callee_number": "8005551000",
            "direction": "inbound",
            "call_start": "2025-01-15 10:00:00",
            "disposition": "answered",
        })
        self.assertEqual(log.customer_number, "5125551234")

    def test_call_log_cdr_primary_id_unique(self):
        self.env["ons.call.log"].create({
            "cdr_primary_id": "CDR-UNIQUE-001",
            "caller_number": "5125559999",
            "direction": "inbound",
        })
        with self.assertRaises(Exception):
            self.env["ons.call.log"].create({
                "cdr_primary_id": "CDR-UNIQUE-001",
                "caller_number": "5125559999",
                "direction": "inbound",
            })

    def test_call_duration_display(self):
        log = self.env["ons.call.log"].create({
            "caller_number": "5125550000",
            "direction": "inbound",
            "call_duration": 125,
        })
        self.assertEqual(log.duration_display, "2:05")

    def test_call_duration_display_zero(self):
        log = self.env["ons.call.log"].create({
            "caller_number": "5125550000",
            "direction": "inbound",
        })
        self.assertEqual(log.duration_display, "0:00")

    # ── Partner Resolution Tests ────────────────────────────────────
    def test_partner_resolution_matched(self):
        """Create a call from a known phone → matched."""
        log = self.env["ons.call.log"].create({
            "caller_number": "+15125551234",
            "direction": "inbound",
        })
        self.assertEqual(log.partner_id, self.partner)
        self.assertEqual(log.match_status, "matched")

    def test_partner_resolution_new_caller(self):
        """Unknown phone → new_caller."""
        log = self.env["ons.call.log"].create({
            "caller_number": "+19995550000",
            "direction": "inbound",
        })
        self.assertFalse(log.partner_id)
        self.assertEqual(log.match_status, "new_caller")

    def test_partner_resolution_ambiguous(self):
        """Two partners with same phone → ambiguous, no partner set."""
        self.env["res.partner"].create({
            "name": "Jane Doe 3CX",
            "phone": "5125559876",
        })
        self.env["res.partner"].create({
            "name": "Jane Copy 3CX",
            "phone": "5125559876",
        })
        log = self.env["ons.call.log"].create({
            "caller_number": "+15125559876",
            "direction": "inbound",
        })
        self.assertFalse(log.partner_id)
        self.assertEqual(log.match_status, "ambiguous")

    def test_re_resolve_partner(self):
        """Manual re-resolution after partner is created."""
        log = self.env["ons.call.log"].create({
            "caller_number": "+18005550001",
            "direction": "inbound",
        })
        self.assertEqual(log.match_status, "new_caller")
        # Create partner with that phone
        self.env["res.partner"].create({
            "name": "Late Partner",
            "phone": "8005550001",
        })
        log.action_resolve_partner()
        self.assertEqual(log.match_status, "matched")
        self.assertEqual(log.partner_id.name, "Late Partner")

    # ── Create Interaction from Call Log ─────────────────────────────
    def test_create_interaction_from_call_log(self):
        log = self.env["ons.call.log"].create({
            "cdr_primary_id": "CDR-INT-001",
            "caller_number": "+15125551234",
            "direction": "inbound",
            "call_start": "2025-01-15 10:00:00",
            "call_end": "2025-01-15 10:05:00",
            "call_duration": 300,
            "talk_duration": 280,
            "queue_name": "First Time Caller",
            "disposition": "answered",
            "has_recording": True,
            "recording_url": "https://example.com/rec/001",
        })
        result = log.action_create_interaction()
        self.assertTrue(log.interaction_id)
        interaction = log.interaction_id
        self.assertEqual(interaction.interaction_type, "phone")
        self.assertEqual(interaction.direction, "inbound")
        self.assertEqual(interaction.threecx_cdr_id, "CDR-INT-001")
        self.assertEqual(interaction.call_log_id, log)
        self.assertEqual(interaction.call_duration, 300)
        self.assertEqual(interaction.talk_duration, 280)
        self.assertEqual(interaction.queue_name, "First Time Caller")
        self.assertEqual(interaction.disposition, "answered")
        self.assertTrue(interaction.has_recording)
        self.assertEqual(interaction.partner_id, self.partner)
        # Returns act_window action
        self.assertEqual(result["type"], "ir.actions.act_window")
        self.assertEqual(result["res_model"], "ons.interaction")

    def test_create_interaction_duplicate_raises(self):
        log = self.env["ons.call.log"].create({
            "cdr_primary_id": "CDR-INT-DUP",
            "caller_number": "5125550000",
            "direction": "inbound",
        })
        log.action_create_interaction()
        with self.assertRaises(UserError):
            log.action_create_interaction()

    # ── Active Call Tests ───────────────────────────────────────────
    def test_active_call_creation(self):
        call = self.env["ons.active.call"].create({
            "threecx_call_id": "3cx-active-001",
            "caller_number": "5125551234",
            "callee_number": "8001",
            "direction": "inbound",
            "started_at": "2025-01-15 10:00:00",
        })
        self.assertEqual(call.threecx_call_id, "3cx-active-001")

    def test_active_call_unique_constraint(self):
        self.env["ons.active.call"].create({
            "threecx_call_id": "3cx-unique-001",
            "direction": "inbound",
        })
        with self.assertRaises(Exception):
            self.env["ons.active.call"].create({
                "threecx_call_id": "3cx-unique-001",
                "direction": "inbound",
            })

    def test_active_call_cleanup_stale(self):
        """Stale calls (>1 hour) should be cleaned up."""
        from datetime import timedelta
        old_time = (self.env.cr.now() - timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S")
        fresh_time = self.env.cr.now().strftime("%Y-%m-%d %H:%M:%S")
        stale = self.env["ons.active.call"].create({
            "threecx_call_id": "3cx-stale-001",
            "direction": "inbound",
            "started_at": old_time,
        })
        fresh = self.env["ons.active.call"].create({
            "threecx_call_id": "3cx-fresh-001",
            "direction": "inbound",
            "started_at": fresh_time,
        })
        self.env["ons.active.call"]._cron_cleanup_stale()
        self.assertFalse(stale.exists())
        self.assertTrue(fresh.exists())

    # ── Agent Status Tests ──────────────────────────────────────────
    def test_agent_status_creation(self):
        status = self.env["ons.agent.status"].create({
            "extension": "1050",
            "user_id": self.test_user.id,
            "agent_name": "Agent Smith",
            "status": "available",
        })
        self.assertEqual(status.status, "available")
        self.assertIn("Available", status.display_name)

    def test_agent_status_extension_unique(self):
        self.env["ons.agent.status"].create({
            "extension": "9999",
            "status": "offline",
        })
        with self.assertRaises(Exception):
            self.env["ons.agent.status"].create({
                "extension": "9999",
                "status": "available",
            })

    # ── Call Log Display Name ───────────────────────────────────────
    def test_call_log_display_name(self):
        log = self.env["ons.call.log"].create({
            "caller_number": "+15125551234",
            "direction": "inbound",
            "call_start": "2025-01-15 10:00:00",
        })
        self.assertIn("IN", log.display_name)
        self.assertIn("5125551234", log.display_name)

    # ── Disposition Values ──────────────────────────────────────────
    def test_call_log_disposition_values(self):
        for disp in ("answered", "missed", "abandoned", "transferred", "voicemail", "no_answer"):
            log = self.env["ons.call.log"].create({
                "caller_number": "5125550000",
                "direction": "inbound",
                "disposition": disp,
            })
            self.assertEqual(log.disposition, disp)

    # ── Cron stubs don't crash ──────────────────────────────────────
    def test_cron_sync_from_3cx_noop(self):
        """CDR sync stub runs without error when no host configured."""
        self.env["ons.call.log"]._cron_sync_from_3cx()

    def test_cron_sync_active_calls_noop(self):
        self.env["ons.active.call"]._cron_sync_active_calls()

    def test_cron_sync_agent_status_noop(self):
        self.env["ons.agent.status"]._cron_sync_agent_status()
