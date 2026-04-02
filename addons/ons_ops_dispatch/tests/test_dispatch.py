# -*- coding: utf-8 -*-
from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestDispatch(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))

        cls.user = cls.env["res.users"].create({
            "name": "Dispatch Agent",
            "login": "dispatch_test_agent",
            "email": "dispatch@test.com",
        })

        cls.partner = cls.env["res.partner"].create({
            "name": "Jane Customer",
            "phone": "5125559999",
            "city": "Austin",
            "street": "100 Main St",
            "zip": "78701",
        })

        # Ensure statuses exist (loaded from data seed)
        cls.status_draft = cls.env["ons.dispatch.status"].search([("code", "=", "draft")], limit=1)
        cls.status_sent = cls.env["ons.dispatch.status"].search([("code", "=", "sent")], limit=1)
        cls.status_has_applicants = cls.env["ons.dispatch.status"].search([("code", "=", "has_applicants")], limit=1)
        cls.status_assigned = cls.env["ons.dispatch.status"].search([("code", "=", "assigned")], limit=1)
        cls.status_confirmed = cls.env["ons.dispatch.status"].search([("code", "=", "confirmed")], limit=1)
        cls.status_in_progress = cls.env["ons.dispatch.status"].search([("code", "=", "in_progress")], limit=1)
        cls.status_completed = cls.env["ons.dispatch.status"].search([("code", "=", "completed")], limit=1)
        cls.status_cancelled = cls.env["ons.dispatch.status"].search([("code", "=", "cancelled")], limit=1)

        cls.cancel_reason = cls.env["ons.dispatch.cancellation.reason"].search([], limit=1)

    def _create_dispatch(self, **kwargs):
        vals = {
            "title": "Test Job — Austin",
            "partner_id": self.partner.id,
            "city": "Austin",
        }
        vals.update(kwargs)
        return self.env["ons.dispatch"].create(vals)

    # ── Basic creation ──────────────────────────────────────────────
    def test_dispatch_creation(self):
        d = self._create_dispatch()
        self.assertTrue(d.name.startswith("DSP-"))
        self.assertEqual(d.dispatch_status, "draft")
        self.assertFalse(d.is_terminal)

    def test_dispatch_auto_checklist(self):
        """Dispatch creation populates checklist from config."""
        d = self._create_dispatch()
        active_configs = self.env["ons.dispatch.checklist.config"].search([("is_active", "=", True)])
        self.assertEqual(len(d.checklist_ids), len(active_configs))

    def test_dispatch_activity_log_on_create(self):
        d = self._create_dispatch()
        self.assertTrue(d.activity_log_ids)
        self.assertEqual(d.activity_log_ids[0].event_type, "created")

    # ── Status transitions ──────────────────────────────────────────
    def test_draft_to_sent(self):
        d = self._create_dispatch()
        d.action_change_status("sent")
        self.assertEqual(d.dispatch_status, "sent")

    def test_sent_to_has_applicants(self):
        d = self._create_dispatch()
        d.action_change_status("sent")
        d.action_change_status("has_applicants")
        self.assertEqual(d.dispatch_status, "has_applicants")

    def test_blocked_transition(self):
        """Cannot go from draft directly to completed."""
        d = self._create_dispatch()
        with self.assertRaises(UserError):
            d.action_change_status("completed")

    def test_terminal_status_no_transitions(self):
        """Completed dispatch cannot transition further."""
        d = self._create_dispatch()
        d.action_change_status("sent")
        d.action_change_status("has_applicants")
        d.action_change_status("assigned")
        d.action_change_status("confirmed")
        d.action_change_status("in_progress")
        d.action_change_status("completed")
        self.assertTrue(d.is_terminal)
        with self.assertRaises(UserError):
            d.action_change_status("cancelled", reason="too late")

    def test_cancelled_is_terminal(self):
        d = self._create_dispatch()
        d.action_change_status("cancelled", reason="Test cancel")
        self.assertTrue(d.is_terminal)
        self.assertIn("Test cancel", d.cancellation_reason or "")

    def test_cancel_requires_reason(self):
        d = self._create_dispatch()
        with self.assertRaises(UserError):
            d.action_change_status("cancelled")

    def test_void_from_draft(self):
        d = self._create_dispatch()
        d.action_change_status("voided", reason="Bad entry")
        self.assertEqual(d.dispatch_status, "voided")
        self.assertTrue(d.is_terminal)

    def test_void_blocked_after_assigned(self):
        """Cannot void once worker is assigned."""
        d = self._create_dispatch()
        d.action_change_status("sent")
        d.action_change_status("has_applicants")
        d.action_change_status("assigned")
        with self.assertRaises(UserError):
            d.action_change_status("voided", reason="Oops")

    # ── Approval flow ───────────────────────────────────────────────
    def test_approval_flow(self):
        d = self._create_dispatch(requires_approval=True)
        d.action_send()
        self.assertEqual(d.dispatch_status, "pending_approval")
        d.action_approve()
        self.assertEqual(d.dispatch_status, "sent")
        self.assertTrue(d.approved_at)

    def test_send_without_approval_goes_direct(self):
        d = self._create_dispatch(requires_approval=False)
        d.action_send()
        self.assertEqual(d.dispatch_status, "sent")

    # ── Applicants ──────────────────────────────────────────────────
    def test_applicant_accept(self):
        d = self._create_dispatch()
        d.action_change_status("sent")
        d.action_change_status("has_applicants")
        applicant = self.env["ons.dispatch.applicant"].create({
            "dispatch_id": d.id,
            "worker_name": "Bob Tech",
            "worker_rating": 4.5,
            "proposed_rate": 75.0,
        })
        applicant.action_accept()
        self.assertEqual(applicant.status, "accepted")
        self.assertEqual(d.assigned_worker_name, "Bob Tech")
        self.assertEqual(d.dispatch_status, "assigned")

    def test_applicant_reject(self):
        d = self._create_dispatch()
        d.action_change_status("sent")
        d.action_change_status("has_applicants")
        applicant = self.env["ons.dispatch.applicant"].create({
            "dispatch_id": d.id,
            "worker_name": "Bad Tech",
        })
        applicant.action_reject("Low rating")
        self.assertEqual(applicant.status, "rejected")

    def test_only_one_accepted_applicant(self):
        d = self._create_dispatch()
        d.action_change_status("sent")
        d.action_change_status("has_applicants")
        a1 = self.env["ons.dispatch.applicant"].create({
            "dispatch_id": d.id,
            "worker_name": "Tech A",
        })
        a2 = self.env["ons.dispatch.applicant"].create({
            "dispatch_id": d.id,
            "worker_name": "Tech B",
        })
        a1.action_accept()
        with self.assertRaises(UserError):
            a2.action_accept()

    def test_applicant_counts(self):
        d = self._create_dispatch()
        self.env["ons.dispatch.applicant"].create({
            "dispatch_id": d.id,
            "worker_name": "Tech X",
        })
        self.env["ons.dispatch.applicant"].create({
            "dispatch_id": d.id,
            "worker_name": "Tech Y",
            "status": "rejected",
        })
        d.invalidate_recordset()
        self.assertEqual(d.applicant_count, 2)
        self.assertEqual(d.pending_applicant_count, 1)

    # ── Checklist ───────────────────────────────────────────────────
    def test_checklist_toggle(self):
        d = self._create_dispatch()
        item = d.checklist_ids[0]
        self.assertFalse(item.completed)
        item.action_toggle_complete()
        self.assertTrue(item.completed)
        self.assertTrue(item.completed_by)
        item.action_toggle_complete()
        self.assertFalse(item.completed)

    def test_checklist_progress(self):
        d = self._create_dispatch()
        total = len(d.checklist_ids)
        self.assertGreater(total, 0)
        d.checklist_ids[0].action_toggle_complete()
        d.invalidate_recordset()
        expected = (1 / total) * 100
        self.assertAlmostEqual(d.checklist_progress, expected, places=1)

    # ── Needs action ────────────────────────────────────────────────
    def test_needs_action_has_applicants(self):
        d = self._create_dispatch()
        d.action_change_status("sent")
        d.action_change_status("has_applicants")
        d.invalidate_recordset()
        self.assertTrue(d.needs_action)

    def test_needs_action_false_for_draft(self):
        d = self._create_dispatch()
        d.invalidate_recordset()
        self.assertFalse(d.needs_action)

    # ── Reminders ───────────────────────────────────────────────────
    def test_reminder_creation(self):
        d = self._create_dispatch(scheduled_start="2026-06-15 14:00:00")
        reminder = self.env["ons.dispatch.reminder"].create({
            "dispatch_id": d.id,
            "minutes_before": 30,
            "scheduled_for": "2026-06-15 13:30:00",
        })
        self.assertFalse(reminder.sent)
        reminder.action_mark_sent()
        self.assertTrue(reminder.sent)

    # ── Voice call ──────────────────────────────────────────────────
    def test_voice_call_creation(self):
        d = self._create_dispatch()
        vc = self.env["ons.dispatch.voice.call"].create({
            "dispatch_id": d.id,
            "call_type": "customer_reminder",
            "target_phone": "5125559999",
            "target_type": "customer",
        })
        self.assertEqual(vc.status, "queued")
        self.assertEqual(vc.attempt_number, 1)

    # ── Activity log ────────────────────────────────────────────────
    def test_activity_log_on_status_change(self):
        d = self._create_dispatch()
        initial_count = len(d.activity_log_ids)
        d.action_change_status("sent")
        d.invalidate_recordset()
        self.assertGreater(len(d.activity_log_ids), initial_count)
        last_log = d.activity_log_ids.sorted("create_date", reverse=True)[0]
        self.assertEqual(last_log.event_type, "status_change")

    # ── Case integration ────────────────────────────────────────────
    def test_case_dispatch_count(self):
        """Case tracks dispatch count."""
        # Create minimal case
        stage = self.env["ons.case.stage"].search([], limit=1)
        case = self.env["ons.case"].create({
            "partner_id": self.partner.id,
            "issue_description": "Broken laptop",
            "stage_id": stage.id if stage else False,
        })
        self._create_dispatch(case_id=case.id)
        case.invalidate_recordset()
        self.assertEqual(case.dispatch_count, 1)

    def test_create_from_case(self):
        stage = self.env["ons.case.stage"].search([], limit=1)
        case = self.env["ons.case"].create({
            "partner_id": self.partner.id,
            "issue_description": "Setup network printer",
            "stage_id": stage.id if stage else False,
        })
        dispatch = self.env["ons.dispatch"].create_from_case(case)
        self.assertEqual(dispatch.case_id, case)
        self.assertEqual(dispatch.partner_id, self.partner)
        self.assertIn("Austin", dispatch.title)
        self.assertEqual(dispatch.contact_phone, "5125559999")

    # ── Full lifecycle ──────────────────────────────────────────────
    def test_full_lifecycle(self):
        """Walk through entire dispatch lifecycle."""
        d = self._create_dispatch()
        d.action_send()
        self.assertEqual(d.dispatch_status, "sent")

        d.action_change_status("has_applicants")
        a = self.env["ons.dispatch.applicant"].create({
            "dispatch_id": d.id,
            "worker_name": "Pro Tech",
            "proposed_rate": 100.0,
        })
        a.action_accept()
        self.assertEqual(d.dispatch_status, "assigned")

        d.action_confirm()
        self.assertEqual(d.dispatch_status, "confirmed")
        self.assertTrue(d.confirmed_at)

        d.action_start()
        self.assertEqual(d.dispatch_status, "in_progress")
        self.assertTrue(d.started_at)

        d.action_complete()
        self.assertEqual(d.dispatch_status, "completed")
        self.assertTrue(d.completed_at)
        self.assertTrue(d.is_terminal)

    def test_timestamps_set_on_transitions(self):
        d = self._create_dispatch()
        d.action_change_status("cancelled", reason="No longer needed")
        self.assertTrue(d.cancelled_at)
