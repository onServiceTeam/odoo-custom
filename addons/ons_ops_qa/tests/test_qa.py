# -*- coding: utf-8 -*-
from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestQA(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))

        # ── Users ───────────────────────────────────────────────
        cls.agent_user = cls.env["res.users"].create({
            "name": "QA Test Agent",
            "login": "qa_test_agent",
            "email": "qa_agent@test.com",
            "group_ids": [
                (4, cls.env.ref("base.group_user").id),
                (4, cls.env.ref("ons_ops_core.group_ops_agent").id),
            ],
        })
        cls.manager_user = cls.env["res.users"].create({
            "name": "QA Test Manager",
            "login": "qa_test_manager",
            "email": "qa_manager@test.com",
            "group_ids": [
                (4, cls.env.ref("base.group_user").id),
                (4, cls.env.ref("ons_ops_core.group_ops_manager").id),
            ],
        })

        # ── Extension for agent ─────────────────────────────────
        cls.extension = cls.env["ons.user.extension"].create({
            "extension": "9050",
            "user_id": cls.agent_user.id,
        })

        # ── Call log ────────────────────────────────────────────
        cls.call_log = cls.env["ons.call.log"].create({
            "caller_number": "5125559999",
            "callee_number": "8005551000",
            "direction": "inbound",
            "call_start": "2026-04-01 10:00:00",
            "call_end": "2026-04-01 10:15:00",
            "disposition": "answered",
            "agent_id": cls.agent_user.id,
        })

        # ── Call type ───────────────────────────────────────────
        cls.call_type = cls.env["ons.qa.call.type"].create({
            "key": "test_intake",
            "name": "Test Intake",
            "phases": "opening,foundations,closing",
            "phase_weights_json": '{"opening": 30, "foundations": 40, "closing": 30}',
            "detection_priority": 100,
        })

        # ── Rules ───────────────────────────────────────────────
        cls.rule_greeting = cls.env["ons.qa.rule"].create({
            "key": "test_greeting",
            "name": "Test Greeting",
            "rule_type": "required",
            "check_type": "phrase_present",
            "phase": "opening",
            "points": 3,
        })
        cls.rule_auto_fail = cls.env["ons.qa.rule"].create({
            "key": "test_banned_word",
            "name": "Test Banned Word",
            "rule_type": "forbidden",
            "check_type": "phrase_present",
            "phase": "opening",
            "is_auto_fail": True,
            "score_cap": 40,
            "penalty_points": 5,
        })

    # ═══════════════════════════════════════════════════════════════
    #  Call Type Tests
    # ═══════════════════════════════════════════════════════════════
    def test_call_type_creation(self):
        self.assertEqual(self.call_type.key, "test_intake")
        self.assertTrue(self.call_type.is_active)

    def test_call_type_unique_key(self):
        with self.assertRaises(Exception):
            self.env["ons.qa.call.type"].create({
                "key": "test_intake",
                "name": "Duplicate",
            })

    def test_call_type_phases_list(self):
        phases = self.call_type.get_phases_list()
        self.assertEqual(phases, ["opening", "foundations", "closing"])

    def test_call_type_phase_weights(self):
        weights = self.call_type.get_phase_weights()
        self.assertEqual(weights["opening"], 30)
        self.assertEqual(weights["foundations"], 40)
        self.assertEqual(sum(weights.values()), 100)

    def test_call_type_empty_phases(self):
        ct = self.env["ons.qa.call.type"].create({
            "key": "test_empty_phases",
            "name": "Empty",
        })
        self.assertEqual(ct.get_phases_list(), [])
        self.assertEqual(ct.get_phase_weights(), {})

    def test_call_type_rule_count(self):
        self.env["ons.qa.call.type.rule"].create({
            "call_type_id": self.call_type.id,
            "rule_id": self.rule_greeting.id,
            "applicability": "required",
        })
        self.call_type.invalidate_recordset()
        self.assertEqual(self.call_type.rule_count, 1)

    # ═══════════════════════════════════════════════════════════════
    #  Rule Tests
    # ═══════════════════════════════════════════════════════════════
    def test_rule_creation(self):
        self.assertEqual(self.rule_greeting.key, "test_greeting")
        self.assertTrue(self.rule_greeting.is_active)
        self.assertEqual(self.rule_greeting.points, 3)

    def test_rule_unique_key(self):
        with self.assertRaises(Exception):
            self.env["ons.qa.rule"].create({
                "key": "test_greeting",
                "name": "Dup",
                "rule_type": "required",
                "check_type": "manual",
            })

    def test_rule_auto_fail_flag(self):
        self.assertTrue(self.rule_auto_fail.is_auto_fail)
        self.assertEqual(self.rule_auto_fail.score_cap, 40)

    # ═══════════════════════════════════════════════════════════════
    #  Call Type Rule Mapping Tests
    # ═══════════════════════════════════════════════════════════════
    def test_call_type_rule_mapping(self):
        mapping = self.env["ons.qa.call.type.rule"].create({
            "call_type_id": self.call_type.id,
            "rule_id": self.rule_greeting.id,
            "applicability": "required",
        })
        self.assertEqual(mapping.applicability, "required")

    def test_call_type_rule_unique_constraint(self):
        self.env["ons.qa.call.type.rule"].create({
            "call_type_id": self.call_type.id,
            "rule_id": self.rule_greeting.id,
            "applicability": "required",
        })
        with self.assertRaises(Exception):
            self.env["ons.qa.call.type.rule"].create({
                "call_type_id": self.call_type.id,
                "rule_id": self.rule_greeting.id,
                "applicability": "optional",
            })

    # ═══════════════════════════════════════════════════════════════
    #  QA Result Creation Tests
    # ═══════════════════════════════════════════════════════════════
    def test_result_creation(self):
        result = self.env["ons.qa.result"].create({
            "call_log_id": self.call_log.id,
            "call_type_id": self.call_type.id,
        })
        self.assertEqual(result.state, "draft")
        self.assertEqual(result.agent_id, self.agent_user)
        self.assertEqual(result.evaluator_id.id, self.env.uid)

    def test_result_agent_computed(self):
        result = self.env["ons.qa.result"].create({
            "call_log_id": self.call_log.id,
        })
        self.assertEqual(result.agent_id, self.agent_user)

    def test_result_effective_score_default(self):
        result = self.env["ons.qa.result"].create({
            "call_log_id": self.call_log.id,
            "final_score": 75.5,
        })
        self.assertAlmostEqual(result.effective_score, 75.5, places=1)

    def test_result_effective_score_override(self):
        result = self.env["ons.qa.result"].create({
            "call_log_id": self.call_log.id,
            "final_score": 75.5,
            "override_score": 80.0,
        })
        self.assertAlmostEqual(result.effective_score, 80.0, places=1)

    # ═══════════════════════════════════════════════════════════════
    #  Grading Flow Tests
    # ═══════════════════════════════════════════════════════════════
    def test_grade_normal(self):
        """Grade without auto-fail goes to ack_pending."""
        result = self.env["ons.qa.result"].create({
            "call_log_id": self.call_log.id,
        })
        result.action_grade(85.0)
        self.assertEqual(result.state, "ack_pending")
        self.assertAlmostEqual(result.final_score, 85.0, places=1)
        self.assertFalse(result.auto_fail)

    def test_grade_auto_fail(self):
        """Grade with auto-fail goes to in_review."""
        result = self.env["ons.qa.result"].create({
            "call_log_id": self.call_log.id,
        })
        result.action_grade(65.0, auto_fail=True, auto_fail_reasons="Banned word", score_cap=40)
        self.assertEqual(result.state, "in_review")
        self.assertTrue(result.auto_fail)
        self.assertTrue(result.needs_human_review)
        self.assertLessEqual(result.final_score, 40.0)

    def test_grade_needs_review(self):
        """Pre-flagged needs_human_review goes to in_review."""
        result = self.env["ons.qa.result"].create({
            "call_log_id": self.call_log.id,
            "needs_human_review": True,
        })
        result.action_grade(70.0)
        self.assertEqual(result.state, "in_review")

    def test_grade_only_draft(self):
        """Cannot grade a non-draft result."""
        result = self.env["ons.qa.result"].create({
            "call_log_id": self.call_log.id,
        })
        result.action_grade(80.0)
        with self.assertRaises(UserError):
            result.action_grade(90.0)

    def test_grade_clamps_score(self):
        """Score is clamped to 0-100."""
        result = self.env["ons.qa.result"].create({
            "call_log_id": self.call_log.id,
        })
        result.action_grade(150.0)
        self.assertLessEqual(result.final_score, 100.0)

    # ═══════════════════════════════════════════════════════════════
    #  Review Flow Tests
    # ═══════════════════════════════════════════════════════════════
    def test_review_normal(self):
        result = self.env["ons.qa.result"].create({
            "call_log_id": self.call_log.id,
            "needs_human_review": True,
        })
        result.action_grade(60.0)
        self.assertEqual(result.state, "in_review")
        result.action_review(notes="Looks OK")
        self.assertEqual(result.state, "ack_pending")
        self.assertTrue(result.reviewed_at)
        self.assertEqual(result.review_notes, "Looks OK")

    def test_review_with_override(self):
        result = self.env["ons.qa.result"].create({
            "call_log_id": self.call_log.id,
            "needs_human_review": True,
        })
        result.action_grade(55.0)
        result.action_review(override_score=70.0)
        self.assertAlmostEqual(result.override_score, 70.0, places=1)
        self.assertAlmostEqual(result.effective_score, 70.0, places=1)

    def test_review_wrong_state(self):
        result = self.env["ons.qa.result"].create({
            "call_log_id": self.call_log.id,
        })
        with self.assertRaises(UserError):
            result.action_review()

    def test_send_to_review(self):
        result = self.env["ons.qa.result"].create({
            "call_log_id": self.call_log.id,
        })
        result.action_grade(80.0)
        self.assertEqual(result.state, "ack_pending")
        result.action_send_to_review()
        self.assertEqual(result.state, "in_review")

    # ═══════════════════════════════════════════════════════════════
    #  Acknowledgement Flow Tests
    # ═══════════════════════════════════════════════════════════════
    def test_acknowledge(self):
        result = self.env["ons.qa.result"].with_user(self.manager_user).create({
            "call_log_id": self.call_log.id,
        })
        result.with_user(self.manager_user).action_grade(80.0)
        # Agent acknowledges
        result_as_agent = result.with_user(self.agent_user)
        result_as_agent.action_acknowledge()
        self.assertEqual(result.state, "acknowledged")
        self.assertTrue(result.acknowledged_at)

    def test_acknowledge_wrong_user(self):
        """Non-agent user cannot acknowledge."""
        result = self.env["ons.qa.result"].create({
            "call_log_id": self.call_log.id,
        })
        result.action_grade(80.0)
        # Manager tries to acknowledge — should fail (not the agent)
        with self.assertRaises(UserError):
            result.action_acknowledge()

    def test_acknowledge_wrong_state(self):
        result = self.env["ons.qa.result"].create({
            "call_log_id": self.call_log.id,
        })
        with self.assertRaises(UserError):
            result.with_user(self.agent_user).action_acknowledge()

    # ═══════════════════════════════════════════════════════════════
    #  Dispute Flow Tests
    # ═══════════════════════════════════════════════════════════════
    def test_dispute(self):
        result = self.env["ons.qa.result"].with_user(self.manager_user).create({
            "call_log_id": self.call_log.id,
        })
        result.with_user(self.manager_user).action_grade(50.0)
        result_as_agent = result.with_user(self.agent_user)
        result_as_agent.action_dispute("I disagree with the opening score")
        self.assertEqual(result.state, "in_review")
        self.assertEqual(result.dispute_reason, "I disagree with the opening score")

    def test_dispute_requires_reason(self):
        result = self.env["ons.qa.result"].with_user(self.manager_user).create({
            "call_log_id": self.call_log.id,
        })
        result.with_user(self.manager_user).action_grade(50.0)
        with self.assertRaises(UserError):
            result.with_user(self.agent_user).action_dispute("")

    def test_dispute_wrong_user(self):
        result = self.env["ons.qa.result"].create({
            "call_log_id": self.call_log.id,
        })
        result.action_grade(50.0)
        with self.assertRaises(UserError):
            result.action_dispute("Unfair")

    def test_dispute_then_review(self):
        """Full dispute cycle: grade → ack_pending → dispute → in_review → review → ack_pending."""
        result = self.env["ons.qa.result"].with_user(self.manager_user).create({
            "call_log_id": self.call_log.id,
        })
        result.with_user(self.manager_user).action_grade(50.0)
        result.with_user(self.agent_user).action_dispute("Disagree")
        self.assertEqual(result.state, "in_review")
        result.with_user(self.manager_user).action_review(notes="Re-reviewed", override_score=65.0)
        self.assertEqual(result.state, "ack_pending")
        self.assertAlmostEqual(result.override_score, 65.0, places=1)

    # ═══════════════════════════════════════════════════════════════
    #  Finding Tests
    # ═══════════════════════════════════════════════════════════════
    def test_finding_creation(self):
        result = self.env["ons.qa.result"].create({
            "call_log_id": self.call_log.id,
        })
        finding = self.env["ons.qa.finding"].create({
            "result_id": result.id,
            "rule_key": "test_greeting",
            "rule_name": "Test Greeting",
            "phase": "opening",
            "status": "hit",
            "points_earned": 3.0,
            "points_possible": 3.0,
        })
        self.assertEqual(finding.status, "hit")
        self.assertEqual(finding.severity, "medium")

    def test_finding_with_evidence(self):
        result = self.env["ons.qa.result"].create({
            "call_log_id": self.call_log.id,
        })
        finding = self.env["ons.qa.finding"].create({
            "result_id": result.id,
            "rule_key": "test_greeting",
            "rule_name": "Test Greeting",
            "phase": "opening",
            "status": "hit",
            "evidence_quote": "Thank you for calling onService",
            "evidence_start_ms": 1000,
            "evidence_end_ms": 3500,
            "evidence_speaker": "agent",
        })
        self.assertEqual(finding.evidence_speaker, "agent")
        self.assertEqual(finding.evidence_start_ms, 1000)

    def test_finding_count_computed(self):
        result = self.env["ons.qa.result"].create({
            "call_log_id": self.call_log.id,
        })
        self.env["ons.qa.finding"].create({
            "result_id": result.id,
            "rule_key": "f1",
            "status": "hit",
        })
        self.env["ons.qa.finding"].create({
            "result_id": result.id,
            "rule_key": "f2",
            "status": "missed",
        })
        result.invalidate_recordset()
        self.assertEqual(result.finding_count, 2)

    # ═══════════════════════════════════════════════════════════════
    #  Coaching Tests
    # ═══════════════════════════════════════════════════════════════
    def test_coaching_creation_from_result(self):
        result = self.env["ons.qa.result"].create({
            "call_log_id": self.call_log.id,
        })
        result.action_grade(70.0)
        coaching = result.action_generate_coaching()
        self.assertEqual(coaching.state, "draft")
        self.assertEqual(coaching.agent_id, self.agent_user)
        self.assertEqual(result.coaching_id, coaching)

    def test_coaching_no_duplicate(self):
        result = self.env["ons.qa.result"].create({
            "call_log_id": self.call_log.id,
        })
        result.action_grade(70.0)
        result.action_generate_coaching()
        with self.assertRaises(UserError):
            result.action_generate_coaching()

    def test_coaching_not_from_draft(self):
        result = self.env["ons.qa.result"].create({
            "call_log_id": self.call_log.id,
        })
        with self.assertRaises(UserError):
            result.action_generate_coaching()

    def test_coaching_publish(self):
        result = self.env["ons.qa.result"].create({
            "call_log_id": self.call_log.id,
        })
        result.action_grade(70.0)
        coaching = result.action_generate_coaching()
        coaching.summary = "Agent needs to work on greeting flow."
        coaching.action_publish()
        self.assertEqual(coaching.state, "published")

    def test_coaching_publish_requires_summary(self):
        result = self.env["ons.qa.result"].create({
            "call_log_id": self.call_log.id,
        })
        result.action_grade(70.0)
        coaching = result.action_generate_coaching()
        with self.assertRaises(UserError):
            coaching.action_publish()

    def test_coaching_acknowledge(self):
        result = self.env["ons.qa.result"].with_user(self.manager_user).create({
            "call_log_id": self.call_log.id,
        })
        result.with_user(self.manager_user).action_grade(70.0)
        coaching = result.with_user(self.manager_user).action_generate_coaching()
        coaching.with_user(self.manager_user).write({"summary": "Work on greeting."})
        coaching.with_user(self.manager_user).action_publish()
        coaching.with_user(self.agent_user).action_acknowledge_coaching()
        self.assertEqual(coaching.state, "acknowledged")

    def test_coaching_acknowledge_wrong_user(self):
        result = self.env["ons.qa.result"].create({
            "call_log_id": self.call_log.id,
        })
        result.action_grade(70.0)
        coaching = result.action_generate_coaching()
        coaching.summary = "Work on greeting."
        coaching.action_publish()
        with self.assertRaises(UserError):
            coaching.action_acknowledge_coaching()

    # ═══════════════════════════════════════════════════════════════
    #  Call Log QA Integration Tests
    # ═══════════════════════════════════════════════════════════════
    def test_call_log_qa_count(self):
        self.assertEqual(self.call_log.qa_result_count, 0)
        self.env["ons.qa.result"].create({
            "call_log_id": self.call_log.id,
            "final_score": 85.0,
        })
        self.call_log.invalidate_recordset()
        self.assertEqual(self.call_log.qa_result_count, 1)
        self.assertAlmostEqual(self.call_log.qa_latest_score, 85.0, places=1)

    # ═══════════════════════════════════════════════════════════════
    #  Seed Data — Verification
    # ═══════════════════════════════════════════════════════════════
    def test_seed_call_types_exist(self):
        """All 8 seeded call types should exist."""
        expected = [
            "first_time_intake", "callback", "verification", "billing",
            "subscription", "transfer", "voicemail", "outbound",
        ]
        for key in expected:
            ct = self.env["ons.qa.call.type"].search([("key", "=", key)])
            self.assertTrue(ct, f"Missing seed call type: {key}")

    def test_seed_rules_exist(self):
        """Core seeded rules should exist."""
        expected = [
            "banned_remote_access", "greeting_proper", "name_capture",
            "issue_identification", "session_pitch", "verification_complete",
            "talk_time_ratio", "dead_air_control",
        ]
        for key in expected:
            rule = self.env["ons.qa.rule"].search([("key", "=", key)])
            self.assertTrue(rule, f"Missing seed rule: {key}")

    # ═══════════════════════════════════════════════════════════════
    #  Deterministic Protection Tests
    # ═══════════════════════════════════════════════════════════════
    def test_qa_result_does_not_change_call_log(self):
        """QA result creation must not alter call log fields."""
        original_disposition = self.call_log.disposition
        original_agent = self.call_log.agent_id
        self.env["ons.qa.result"].create({
            "call_log_id": self.call_log.id,
            "final_score": 90.0,
        })
        self.call_log.invalidate_recordset()
        self.assertEqual(self.call_log.disposition, original_disposition)
        self.assertEqual(self.call_log.agent_id, original_agent)

    def test_full_workflow_end_to_end(self):
        """Complete happy path: create → grade → review → acknowledge."""
        result = self.env["ons.qa.result"].with_user(self.manager_user).create({
            "call_log_id": self.call_log.id,
            "call_type_id": self.call_type.id,
            "needs_human_review": True,
        })
        # Grade
        result.with_user(self.manager_user).action_grade(72.0)
        self.assertEqual(result.state, "in_review")
        # Review
        result.with_user(self.manager_user).action_review(notes="Acceptable")
        self.assertEqual(result.state, "ack_pending")
        # Acknowledge
        result.with_user(self.agent_user).action_acknowledge()
        self.assertEqual(result.state, "acknowledged")
        self.assertTrue(result.acknowledged_at)
