# -*- coding: utf-8 -*-
from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


class TestCaseCreation(TransactionCase):
    """Tests for case creation from leads and interactions."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.driver = cls.env["ons.call.driver"].create({
            "name": "Test Case Driver",
            "code": "TST_CASE_DRV",
            "category": "boot_startup",
        })
        cls.partner = cls.env["res.partner"].create({
            "name": "Case Test Customer",
            "phone": "5559998888",
            "customer_segment": "returning",
        })
        cls.stage_intake = cls.env.ref("ons_ops_cases.stage_intake_submitted")
        cls.stage_triage = cls.env.ref("ons_ops_cases.stage_triage_in_progress")
        cls.stage_oss = cls.env.ref("ons_ops_cases.stage_online_session_started")
        cls.stage_repair = cls.env.ref("ons_ops_cases.stage_repair_in_progress")
        cls.stage_won = cls.env.ref("ons_ops_cases.stage_closed_won")
        cls.stage_lost = cls.env.ref("ons_ops_cases.stage_closed_lost")
        cls.stage_paid = cls.env.ref("ons_ops_cases.stage_paid")
        cls.stage_billing = cls.env.ref("ons_ops_cases.stage_billing_in_progress")
        cls.stage_handoff = cls.env.ref("ons_ops_cases.stage_handoff_to_assisting")
        cls.stage_verification = cls.env.ref("ons_ops_cases.stage_ready_for_verification")
        cls.stage_callback = cls.env.ref("ons_ops_cases.stage_callback_scheduled")

    def _create_interaction(self, **kw):
        vals = {
            "interaction_type": "phone",
            "customer_phone": "5559998888",
            "state": "classified",
            "primary_driver_id": self.driver.id,
            "session_path": "session_now",
            "partner_id": self.partner.id,
        }
        vals.update(kw)
        return self.env["ons.interaction"].create(vals)

    def _create_case(self, **kw):
        vals = {
            "partner_id": self.partner.id,
            "primary_driver_id": self.driver.id,
        }
        vals.update(kw)
        return self.env["ons.case"].create(vals)

    # ── Case creation ───────────────────────────────────────────────

    def test_case_creation_generates_sequence(self):
        """Case creation should auto-generate a CASE-YYMMDD-XXXX reference."""
        case = self._create_case()
        self.assertTrue(case.name.startswith("CASE-"), "Expected CASE- prefix, got %s" % case.name)
        self.assertNotEqual(case.name, "New")

    def test_case_default_stage_is_intake(self):
        """New case should default to intake_submitted stage."""
        case = self._create_case()
        self.assertEqual(case.stage_id, self.stage_intake)

    def test_case_requires_partner(self):
        """Case creation without partner should fail."""
        with self.assertRaises(Exception):
            self.env["ons.case"].create({"primary_driver_id": self.driver.id})

    def test_case_from_interaction_session_now(self):
        """action_create_case from session_now interaction."""
        interaction = self._create_interaction(session_path="session_now")
        result = interaction.action_create_case()
        case = self.env["ons.case"].browse(result["res_id"])
        self.assertTrue(case.exists())
        self.assertEqual(case.partner_id, self.partner)
        self.assertEqual(case.source_interaction_id, interaction)
        self.assertEqual(interaction.case_id, case)
        self.assertTrue(case.online_session_started)
        # Should auto-advance to online_session_started stage
        self.assertEqual(case.stage_id, self.stage_oss)

    def test_case_from_interaction_callback(self):
        """action_create_case from callback interaction stays at intake."""
        interaction = self._create_interaction(session_path="callback")
        result = interaction.action_create_case()
        case = self.env["ons.case"].browse(result["res_id"])
        self.assertEqual(case.stage_id, self.stage_intake)
        self.assertFalse(case.online_session_started)

    def test_case_from_interaction_no_session_rejected(self):
        """no_session interaction should not create a case."""
        interaction = self._create_interaction(session_path="no_session")
        with self.assertRaises(UserError):
            interaction.action_create_case()

    def test_case_from_interaction_not_applicable_rejected(self):
        """not_applicable interaction should not create a case."""
        interaction = self._create_interaction(session_path="not_applicable")
        with self.assertRaises(UserError):
            interaction.action_create_case()

    def test_case_from_interaction_requires_partner(self):
        """Interaction without partner should reject case creation."""
        interaction = self._create_interaction(partner_id=False)
        with self.assertRaises(UserError):
            interaction.action_create_case()

    def test_case_from_interaction_requires_classified(self):
        """Unclassified interaction should reject case creation."""
        interaction = self._create_interaction(state="new")
        with self.assertRaises(UserError):
            interaction.action_create_case()

    def test_duplicate_case_from_interaction_rejected(self):
        """Cannot create two cases from the same interaction."""
        interaction = self._create_interaction()
        interaction.action_create_case()
        with self.assertRaises(UserError):
            interaction.action_create_case()


class TestCaseFromLead(TransactionCase):
    """Tests for lead → case conversion."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.driver = cls.env["ons.call.driver"].create({
            "name": "Test Lead Case Driver",
            "code": "TST_LCASE_DRV",
            "category": "boot_startup",
        })
        cls.partner = cls.env["res.partner"].create({
            "name": "Lead Case Customer",
            "phone": "5557776666",
            "customer_segment": "new",
        })

    def _create_interaction(self, **kw):
        vals = {
            "interaction_type": "phone",
            "customer_phone": "5557776666",
            "state": "classified",
            "primary_driver_id": self.driver.id,
            "session_path": "session_now",
            "partner_id": self.partner.id,
        }
        vals.update(kw)
        return self.env["ons.interaction"].create(vals)

    def test_convert_qualified_lead_to_case(self):
        """Qualified lead with service-ready interaction converts to case."""
        interaction = self._create_interaction()
        Lead = self.env["crm.lead"]
        lead = Lead.action_create_lead_from_interaction(interaction)
        self.assertTrue(lead.is_convertible)
        result = lead.action_convert_to_case()
        case = self.env["ons.case"].browse(result["res_id"])
        self.assertTrue(case.exists())
        self.assertEqual(case.lead_id, lead)
        self.assertEqual(lead.case_id, case)
        self.assertEqual(case.partner_id, self.partner)

    def test_convert_lead_already_has_case_returns_existing(self):
        """Lead that already has a case should navigate to it."""
        interaction = self._create_interaction()
        Lead = self.env["crm.lead"]
        lead = Lead.action_create_lead_from_interaction(interaction)
        result1 = lead.action_convert_to_case()
        case = self.env["ons.case"].browse(result1["res_id"])
        # Second conversion should return the existing case
        result2 = lead.action_convert_to_case()
        self.assertEqual(result2["res_id"], case.id)

    def test_non_convertible_lead_rejected(self):
        """Lead without is_convertible=True rejected."""
        # Create a lead for a no_session interaction — not convertible
        interaction = self._create_interaction(session_path="no_session")
        Lead = self.env["crm.lead"]
        # Manually create lead (bypassing normal logic which would reject)
        lead = Lead.create({
            "name": "Test Non-Convertible",
            "type": "lead",
            "partner_id": self.partner.id,
            "phone": "5557776666",
            "interaction_id": interaction.id,
            "lead_type": "inquiry",
        })
        self.assertFalse(lead.is_convertible)
        with self.assertRaises(UserError):
            lead.action_convert_to_case()


class TestStageTransitions(TransactionCase):
    """Tests for stage transition validation."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({
            "name": "Transition Test Customer",
            "phone": "5554443333",
        })
        cls.stage_intake = cls.env.ref("ons_ops_cases.stage_intake_submitted")
        cls.stage_triage = cls.env.ref("ons_ops_cases.stage_triage_in_progress")
        cls.stage_oss = cls.env.ref("ons_ops_cases.stage_online_session_started")
        cls.stage_repair = cls.env.ref("ons_ops_cases.stage_repair_in_progress")
        cls.stage_won = cls.env.ref("ons_ops_cases.stage_closed_won")
        cls.stage_lost = cls.env.ref("ons_ops_cases.stage_closed_lost")
        cls.stage_paid = cls.env.ref("ons_ops_cases.stage_paid")
        cls.stage_billing = cls.env.ref("ons_ops_cases.stage_billing_in_progress")
        cls.stage_handoff = cls.env.ref("ons_ops_cases.stage_handoff_to_assisting")
        cls.stage_verification = cls.env.ref("ons_ops_cases.stage_ready_for_verification")
        cls.stage_callback = cls.env.ref("ons_ops_cases.stage_callback_scheduled")
        cls.stage_onsite = cls.env.ref("ons_ops_cases.stage_onsite_dispatched")

    def _create_case(self, **kw):
        vals = {"partner_id": self.partner.id}
        vals.update(kw)
        return self.env["ons.case"].create(vals)

    def test_valid_transition_intake_to_triage(self):
        """intake_submitted → triage_in_progress is allowed."""
        case = self._create_case()
        case.stage_id = self.stage_triage
        self.assertEqual(case.stage_id, self.stage_triage)

    def test_valid_transition_intake_to_oss(self):
        """intake_submitted → online_session_started is allowed."""
        case = self._create_case()
        case.stage_id = self.stage_oss
        self.assertEqual(case.stage_id, self.stage_oss)

    def test_invalid_transition_intake_to_repair(self):
        """intake_submitted → repair_in_progress is NOT allowed (must go through triage/oss)."""
        case = self._create_case()
        with self.assertRaises(UserError):
            case.stage_id = self.stage_repair

    def test_invalid_transition_intake_to_paid(self):
        """intake_submitted → paid is NOT allowed."""
        case = self._create_case()
        with self.assertRaises(UserError):
            case.stage_id = self.stage_paid

    def test_closed_won_is_terminal(self):
        """closed_won has no outgoing transitions."""
        case = self._create_case()
        # Walk to closed_won
        case.stage_id = self.stage_oss
        case.stage_id = self.stage_handoff
        case.stage_id = self.stage_repair
        case.stage_id = self.stage_verification
        case.stage_id = self.stage_billing
        case.stage_id = self.stage_paid
        case.stage_id = self.stage_won
        self.assertTrue(case.is_closed)
        self.assertTrue(case.is_won)
        with self.assertRaises(UserError):
            case.stage_id = self.stage_triage

    def test_closed_lost_is_terminal(self):
        """closed_lost has no outgoing transitions."""
        case = self._create_case()
        case.stage_id = self.stage_lost
        self.assertTrue(case.is_closed)
        with self.assertRaises(UserError):
            case.stage_id = self.stage_triage

    def test_full_happy_path(self):
        """Walk the full happy path: intake → triage → oss → handoff → repair → verify → billing → paid → won."""
        case = self._create_case()
        case.stage_id = self.stage_triage
        case.stage_id = self.stage_oss
        case.stage_id = self.stage_handoff
        case.stage_id = self.stage_repair
        case.stage_id = self.stage_verification
        case.stage_id = self.stage_billing
        case.stage_id = self.stage_paid
        case.stage_id = self.stage_won
        self.assertTrue(case.is_won)
        self.assertTrue(case.is_closed)


class TestStageHistory(TransactionCase):
    """Tests for stage history audit trail."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({
            "name": "History Test Customer",
            "phone": "5551110000",
        })
        cls.stage_intake = cls.env.ref("ons_ops_cases.stage_intake_submitted")
        cls.stage_triage = cls.env.ref("ons_ops_cases.stage_triage_in_progress")
        cls.stage_oss = cls.env.ref("ons_ops_cases.stage_online_session_started")

    def _create_case(self, **kw):
        vals = {"partner_id": self.partner.id}
        vals.update(kw)
        return self.env["ons.case"].create(vals)

    def test_initial_stage_logged(self):
        """Creating a case logs the initial stage entry."""
        case = self._create_case()
        self.assertEqual(len(case.stage_history_ids), 1)
        self.assertEqual(case.stage_history_ids[0].stage_id, self.stage_intake)
        self.assertFalse(case.stage_history_ids[0].exited_at)

    def test_transition_creates_history(self):
        """Moving stage creates a new history entry and closes the old one."""
        case = self._create_case()
        case.stage_id = self.stage_triage
        history = case.stage_history_ids.sorted("entered_at")
        self.assertEqual(len(history), 2)
        # First entry should be closed
        self.assertTrue(history[0].exited_at)
        self.assertEqual(history[0].stage_id, self.stage_intake)
        # Second entry should be open
        self.assertFalse(history[1].exited_at)
        self.assertEqual(history[1].stage_id, self.stage_triage)

    def test_duration_computed_on_exit(self):
        """Duration is computed when exited_at is set."""
        case = self._create_case()
        case.stage_id = self.stage_triage
        closed_entry = case.stage_history_ids.filtered(lambda h: h.exited_at)
        self.assertTrue(closed_entry)
        self.assertGreaterEqual(closed_entry[0].duration_hours, 0.0)


class TestCaseAging(TransactionCase):
    """Tests for aging bucket computation."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({
            "name": "Aging Test Customer",
            "phone": "5552223344",
        })

    def test_new_case_aging_bucket(self):
        """Newly created case should be in 0-4h bucket."""
        case = self.env["ons.case"].create({"partner_id": self.partner.id})
        self.assertEqual(case.aging_bucket, "0_4h")
        self.assertFalse(case.is_stale)

    def test_closed_case_no_aging(self):
        """Closed case should have no aging."""
        stage_lost = self.env.ref("ons_ops_cases.stage_closed_lost")
        case = self.env["ons.case"].create({"partner_id": self.partner.id})
        case.stage_id = stage_lost
        self.assertFalse(case.aging_bucket)
        self.assertFalse(case.is_stale)


class TestCaseReopen(TransactionCase):
    """Tests for reopening closed cases."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({
            "name": "Reopen Test Customer",
            "phone": "5556667788",
        })
        cls.stage_lost = cls.env.ref("ons_ops_cases.stage_closed_lost")
        cls.stage_triage = cls.env.ref("ons_ops_cases.stage_triage_in_progress")

    def test_reopen_closed_case(self):
        """Reopening a closed case returns it to triage."""
        case = self.env["ons.case"].create({"partner_id": self.partner.id})
        case.stage_id = self.stage_lost
        self.assertTrue(case.is_closed)
        case.action_reopen()
        self.assertEqual(case.stage_id, self.stage_triage)
        self.assertFalse(case.is_closed)

    def test_reopen_non_closed_case_rejected(self):
        """Cannot reopen a case that is not closed."""
        case = self.env["ons.case"].create({"partner_id": self.partner.id})
        with self.assertRaises(UserError):
            case.action_reopen()


class TestCaseStageData(TransactionCase):
    """Tests for seed data integrity."""

    def test_twelve_stages_loaded(self):
        """All 12 canonical stages should be loaded."""
        stages = self.env["ons.case.stage"].search([])
        self.assertEqual(len(stages), 12)

    def test_stage_codes_unique(self):
        """Each stage should have a unique code."""
        stages = self.env["ons.case.stage"].search([])
        codes = stages.mapped("code")
        self.assertEqual(len(codes), len(set(codes)))

    def test_terminal_stages(self):
        """closed_won and closed_lost should be marked as closed."""
        won = self.env.ref("ons_ops_cases.stage_closed_won")
        lost = self.env.ref("ons_ops_cases.stage_closed_lost")
        self.assertTrue(won.is_closed)
        self.assertTrue(won.is_won)
        self.assertTrue(lost.is_closed)
        self.assertFalse(lost.is_won)

    def test_actions_loadable(self):
        """Session tracker and kanban actions should load."""
        tracker = self.env.ref("ons_ops_cases.action_session_tracker")
        self.assertEqual(tracker.res_model, "ons.case")
        kanban = self.env.ref("ons_ops_cases.action_case_kanban")
        self.assertEqual(kanban.res_model, "ons.case")
