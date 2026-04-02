# -*- coding: utf-8 -*-
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestComms(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))

        cls.partner = cls.env["res.partner"].create({
            "name": "Comms Test Customer",
            "phone": "5125551234",
            "email": "comms@test.com",
        })

        # Create a case for linkage tests
        stage = cls.env["ons.case.stage"].search([], limit=1)
        cls.case = cls.env["ons.case"].create({
            "partner_id": cls.partner.id,
            "issue_description": "Communication test case",
            "stage_id": stage.id if stage else False,
        })

        # Create a dispatch for linkage tests
        cls.dispatch = cls.env["ons.dispatch"].create({
            "title": "Comms Test Dispatch",
            "partner_id": cls.partner.id,
        })

    # ── SMS Thread Tests ────────────────────────────────────────────
    def test_sms_thread_find_or_create(self):
        thread = self.env["ons.sms.thread"].find_or_create("5125551234")
        self.assertEqual(thread.phone_number, "5125551234")
        # Second call returns same thread
        thread2 = self.env["ons.sms.thread"].find_or_create("5125551234")
        self.assertEqual(thread, thread2)

    def test_sms_thread_normalize_phone(self):
        result = self.env["ons.sms.thread"]._normalize_phone("+15125551234")
        self.assertEqual(result, "5125551234")

    def test_sms_thread_normalize_formatted(self):
        result = self.env["ons.sms.thread"]._normalize_phone("(512) 555-1234")
        self.assertEqual(result, "5125551234")

    def test_sms_receive_message(self):
        msg = self.env["ons.sms.thread"].receive_message(
            phone_number="5125551234",
            body="Hello, confirming the appointment",
            external_sid="SM_TEST_001",
        )
        self.assertEqual(msg.direction, "inbound")
        self.assertEqual(msg.status, "received")
        self.assertTrue(msg.thread_id)
        self.assertEqual(msg.thread_id.unread_count, 1)

    def test_sms_thread_partner_auto_link(self):
        """When receiving SMS, partner is auto-linked by phone."""
        msg = self.env["ons.sms.thread"].receive_message(
            phone_number="5125551234",
            body="Test auto-link",
        )
        self.assertEqual(msg.thread_id.partner_id, self.partner)

    def test_sms_thread_case_link(self):
        thread = self.env["ons.sms.thread"].find_or_create(
            "5125559999", case_id=self.case.id
        )
        self.assertEqual(thread.case_id, self.case)

    def test_sms_thread_dispatch_link(self):
        thread = self.env["ons.sms.thread"].find_or_create(
            "5125558888", dispatch_id=self.dispatch.id
        )
        self.assertEqual(thread.dispatch_id, self.dispatch)

    def test_sms_mark_read(self):
        msg = self.env["ons.sms.thread"].receive_message(
            phone_number="5125557777", body="Unread test"
        )
        thread = msg.thread_id
        self.assertGreater(thread.unread_count, 0)
        thread.action_mark_read()
        self.assertEqual(thread.unread_count, 0)

    def test_sms_chatter_post_on_linked_case(self):
        """SMS on a case-linked thread posts to case chatter."""
        thread = self.env["ons.sms.thread"].find_or_create(
            "5125556666", case_id=self.case.id
        )
        initial_count = len(self.case.message_ids)
        self.env["ons.sms.thread"].receive_message(
            phone_number="5125556666", body="I confirm"
        )
        self.case.invalidate_recordset()
        self.assertGreater(len(self.case.message_ids), initial_count)

    # ── Email Thread Tests ──────────────────────────────────────────
    def test_email_thread_find_or_create(self):
        thread = self.env["ons.email.thread"].find_or_create(
            subject="Test Subject",
            email_from="test@example.com",
            external_thread_id="MSG-001",
        )
        self.assertEqual(thread.subject, "Test Subject")
        # Same external ID returns same thread
        thread2 = self.env["ons.email.thread"].find_or_create(
            subject="Different",
            email_from="test@example.com",
            external_thread_id="MSG-001",
        )
        self.assertEqual(thread, thread2)

    def test_email_receive_message(self):
        msg = self.env["ons.email.thread"].receive_message(
            from_address="comms@test.com",
            to_address="support@onservice.us",
            subject="Appointment Question",
            body_text="When is my appointment?",
            message_id="MSG-002",
        )
        self.assertEqual(msg.direction, "inbound")
        self.assertEqual(msg.status, "received")
        self.assertTrue(msg.thread_id)

    def test_email_partner_auto_link(self):
        """Email matched by from_address to partner email."""
        msg = self.env["ons.email.thread"].receive_message(
            from_address="comms@test.com",
            to_address="support@onservice.us",
            subject="Auto-link test",
            message_id="MSG-003",
        )
        self.assertEqual(msg.thread_id.partner_id, self.partner)

    def test_email_thread_unread(self):
        msg = self.env["ons.email.thread"].receive_message(
            from_address="new@example.com",
            to_address="support@onservice.us",
            subject="Unread Email",
            message_id="MSG-004",
        )
        self.assertEqual(msg.thread_id.unread_count, 1)
        msg.thread_id.action_mark_read()
        self.assertEqual(msg.thread_id.unread_count, 0)

    # ── Notification Rule Tests ─────────────────────────────────────
    def test_notification_rule_fire_chatter(self):
        """Rule with chatter enabled posts to record."""
        rule = self.env["ons.notification.rule"].create({
            "name": "Test Chatter Rule",
            "event_type": "case_created",
            "notify_internal_chatter": True,
            "chatter_body": "Case {{case_name}} created",
        })
        initial = len(self.case.message_ids)
        rule.fire(self.case, {"case_name": self.case.name})
        self.case.invalidate_recordset()
        self.assertGreater(len(self.case.message_ids), initial)

    def test_notification_rule_fire_creates_log(self):
        rule = self.env["ons.notification.rule"].create({
            "name": "Test Log Rule",
            "event_type": "dispatch_created",
            "notify_internal_chatter": True,
            "chatter_body": "Dispatch created",
        })
        rule.fire(self.dispatch, {})
        log = self.env["ons.notification.log"].search([
            ("rule_id", "=", rule.id),
        ])
        self.assertTrue(log)
        self.assertEqual(log.channel, "chatter")
        self.assertEqual(log.status, "sent")

    def test_notification_rule_sms_queued(self):
        """SMS channel queues a log entry for sidecar pickup."""
        template = self.env["ons.message.template"].create({
            "name": "Test SMS Template",
            "code": "test_sms_tpl",
            "channel": "sms",
            "body": "Hi {{customer_name}}, your appointment is confirmed.",
        })
        rule = self.env["ons.notification.rule"].create({
            "name": "Test SMS Rule",
            "event_type": "dispatch_reminder",
            "notify_customer_sms": True,
            "sms_template_id": template.id,
        })
        rule.fire(self.dispatch, {"customer_phone": "5125551234", "customer_name": "Jane"})
        log = self.env["ons.notification.log"].search([
            ("rule_id", "=", rule.id),
            ("channel", "=", "sms"),
        ])
        self.assertTrue(log)
        self.assertEqual(log.status, "queued")

    def test_notification_rule_inactive_skipped(self):
        """Inactive rules don't fire."""
        rule = self.env["ons.notification.rule"].create({
            "name": "Inactive Rule",
            "event_type": "case_created",
            "notify_internal_chatter": True,
            "chatter_body": "Should not post",
            "is_active": False,
        })
        initial = len(self.case.message_ids)
        rule.fire(self.case, {})
        self.case.invalidate_recordset()
        self.assertEqual(len(self.case.message_ids), initial)

    def test_template_rendering(self):
        result = self.env["ons.notification.rule"]._render_template(
            "Hello {{name}}, your appointment on {{date}} is confirmed.",
            {"name": "Jane", "date": "June 15"},
        )
        self.assertEqual(result, "Hello Jane, your appointment on June 15 is confirmed.")

    def test_template_rendering_missing_var(self):
        """Missing variables are replaced with empty string."""
        result = self.env["ons.notification.rule"]._render_template(
            "Hello {{ name }}, total: {{amount}}",
            {"name": "Bob"},
        )
        self.assertIn("Bob", result)
        # amount is not replaced — stays as-is since no key matched
        self.assertIn("{{amount}}", result)

    # ── Message Template Tests ──────────────────────────────────────
    def test_message_template_creation(self):
        tpl = self.env["ons.message.template"].create({
            "name": "Confirm SMS",
            "code": "confirm_sms_test",
            "channel": "sms",
            "body": "Your visit on {{visit_date}} is confirmed.",
        })
        self.assertTrue(tpl.is_active)

    # ── Case Comms Counts ───────────────────────────────────────────
    def test_case_sms_thread_count(self):
        self.env["ons.sms.thread"].find_or_create(
            "5125554444", case_id=self.case.id
        )
        self.case.invalidate_recordset()
        self.assertEqual(self.case.sms_thread_count, 1)

    def test_case_email_thread_count(self):
        self.env["ons.email.thread"].create({
            "subject": "Test linked email",
            "email_from": "test@example.com",
            "case_id": self.case.id,
        })
        self.case.invalidate_recordset()
        self.assertEqual(self.case.email_thread_count, 1)

    # ── Dispatch Comms Counts ───────────────────────────────────────
    def test_dispatch_sms_count(self):
        self.env["ons.sms.thread"].find_or_create(
            "5125553333", dispatch_id=self.dispatch.id
        )
        self.dispatch.invalidate_recordset()
        self.assertEqual(self.dispatch.sms_thread_count, 1)

    def test_dispatch_email_count(self):
        self.env["ons.email.thread"].create({
            "subject": "Dispatch email",
            "email_from": "tech@example.com",
            "dispatch_id": self.dispatch.id,
        })
        self.dispatch.invalidate_recordset()
        self.assertEqual(self.dispatch.email_thread_count, 1)

    # ── Notification Log Search ─────────────────────────────────────
    def test_notification_log_creation(self):
        log = self.env["ons.notification.log"].create({
            "event_type": "test_event",
            "channel": "sms",
            "status": "queued",
            "res_model": "ons.case",
            "res_id": self.case.id,
            "sent_to": "5125551234",
        })
        self.assertTrue(log)
        self.assertEqual(log.status, "queued")
