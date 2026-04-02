# -*- coding: utf-8 -*-
from odoo.tests import TransactionCase, tagged
from odoo.exceptions import UserError


@tagged("post_install", "-at_install")
class TestAi(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))

        # Provider
        cls.provider = cls.env["ons.ai.provider"].create({
            "name": "test_provider",
            "display_name_custom": "Test Provider",
            "provider_type": "chat",
            "api_endpoint": "https://test.example.com/v1/chat",
            "is_active": True,
        })

        # Model
        cls.ai_model = cls.env["ons.ai.model"].create({
            "model_id": "test-model-1",
            "display_name_custom": "Test Model",
            "provider_id": cls.provider.id,
            "category": "chat",
            "pricing_tier": "budget",
            "is_available": True,
        })

        cls.ai_model_fallback = cls.env["ons.ai.model"].create({
            "model_id": "test-fallback-1",
            "display_name_custom": "Test Fallback",
            "provider_id": cls.provider.id,
            "category": "chat",
            "pricing_tier": "budget",
            "is_available": True,
        })

        # Task
        cls.task = cls.env["ons.ai.task"].create({
            "task_type": "test_task",
            "display_name_custom": "Test Task",
            "model_id": cls.ai_model.id,
            "fallback_model_id": cls.ai_model_fallback.id,
            "temperature": 0.3,
            "max_tokens": 1000,
            "is_enabled": True,
        })

        # Prompt template
        cls.prompt = cls.env["ons.ai.prompt.template"].create({
            "code": "test_prompt",
            "name": "Test Prompt",
            "task_type": "test_task",
            "system_prompt": "You are a {{role}}. Do {{action}}.",
            "user_prompt_template": "Input: {{input}}",
            "available_variables": "role, action, input",
            "version": 1,
            "is_active": True,
        })

        # Partner and interaction for integration tests
        cls.partner = cls.env["res.partner"].create({
            "name": "AI Test Customer",
            "phone": "5125559876",
        })

        cls.driver = cls.env["ons.call.driver"].search([], limit=1)
        cls.interaction = cls.env["ons.interaction"].create({
            "interaction_type": "phone",
            "direction": "inbound",
            "issue_description": "Customer computer wont boot, shows blue screen",
            "primary_driver_id": cls.driver.id if cls.driver else False,
        })

        stage = cls.env["ons.case.stage"].search([], limit=1)
        cls.case = cls.env["ons.case"].create({
            "partner_id": cls.partner.id,
            "issue_description": "Blue screen issue",
            "summary": "Agent helped with blue screen troubleshooting",
            "stage_id": stage.id if stage else False,
        })

    # ── Provider Tests ──────────────────────────────────────────

    def test_provider_creation(self):
        self.assertEqual(self.provider.name, "test_provider")
        self.assertEqual(self.provider.health_status, "unknown")

    def test_provider_unique_name(self):
        with self.assertRaises(Exception):
            self.env["ons.ai.provider"].create({
                "name": "test_provider",
                "provider_type": "chat",
            })

    def test_provider_mark_healthy(self):
        self.provider.action_mark_healthy()
        self.assertEqual(self.provider.health_status, "healthy")
        self.assertTrue(self.provider.last_health_check)

    def test_provider_mark_down(self):
        self.provider.action_mark_down()
        self.assertEqual(self.provider.health_status, "down")

    # ── Model Tests ─────────────────────────────────────────────

    def test_model_creation(self):
        self.assertEqual(self.ai_model.model_id, "test-model-1")
        self.assertEqual(self.ai_model.provider_id, self.provider)

    def test_model_unique_id(self):
        with self.assertRaises(Exception):
            self.env["ons.ai.model"].create({
                "model_id": "test-model-1",
                "provider_id": self.provider.id,
                "category": "chat",
            })

    # ── Task Tests ──────────────────────────────────────────────

    def test_task_creation(self):
        self.assertEqual(self.task.task_type, "test_task")
        self.assertTrue(self.task.is_enabled)

    def test_task_unique_type(self):
        with self.assertRaises(Exception):
            self.env["ons.ai.task"].create({
                "task_type": "test_task",
                "model_id": self.ai_model.id,
            })

    def test_get_task_config(self):
        config = self.env["ons.ai.task"].get_task_config("test_task")
        self.assertEqual(config["task_type"], "test_task")
        self.assertEqual(config["model_id"], "test-model-1")
        self.assertEqual(config["fallback_model_id"], "test-fallback-1")
        self.assertAlmostEqual(config["temperature"], 0.3, places=2)

    def test_get_task_config_missing(self):
        with self.assertRaises(UserError):
            self.env["ons.ai.task"].get_task_config("nonexistent")

    def test_get_task_config_disabled(self):
        self.task.is_enabled = False
        with self.assertRaises(UserError):
            self.env["ons.ai.task"].get_task_config("test_task")
        self.task.is_enabled = True

    # ── Prompt Template Tests ───────────────────────────────────

    def test_prompt_creation(self):
        self.assertEqual(self.prompt.code, "test_prompt")
        self.assertEqual(self.prompt.version, 1)

    def test_prompt_render(self):
        result = self.env["ons.ai.prompt.template"].render(
            "test_prompt",
            {"role": "classifier", "action": "classify", "input": "hello"},
        )
        self.assertEqual(result["system_prompt"], "You are a classifier. Do classify.")
        self.assertEqual(result["user_prompt"], "Input: hello")
        self.assertEqual(result["version"], 1)

    def test_prompt_render_missing_variable(self):
        """Missing variables should be left as-is, not stripped."""
        result = self.env["ons.ai.prompt.template"].render(
            "test_prompt",
            {"role": "tester"},
        )
        self.assertIn("{{action}}", result["system_prompt"])
        self.assertEqual(result["system_prompt"], "You are a tester. Do {{action}}.")

    def test_prompt_render_nonexistent_code(self):
        result = self.env["ons.ai.prompt.template"].render("nonexistent")
        self.assertEqual(result["system_prompt"], "")
        self.assertEqual(result["version"], 0)

    def test_prompt_new_version(self):
        result = self.prompt.action_new_version()
        new_prompt = self.env["ons.ai.prompt.template"].browse(result["res_id"])
        self.assertEqual(new_prompt.version, 2)
        self.assertTrue(new_prompt.is_active)
        self.assertFalse(self.prompt.is_active)

    def test_prompt_render_uses_latest_active(self):
        """Render should use highest active version."""
        v2 = self.prompt.copy({
            "version": 2,
            "is_active": True,
            "system_prompt": "Version 2: {{role}}",
        })
        self.prompt.is_active = False  # deactivate v1
        result = self.env["ons.ai.prompt.template"].render(
            "test_prompt", {"role": "v2test"},
        )
        self.assertEqual(result["system_prompt"], "Version 2: v2test")
        self.assertEqual(result["version"], 2)
        # cleanup
        v2.unlink()
        self.prompt.is_active = True

    # ── Run Log Tests ───────────────────────────────────────────

    def test_run_log_creation(self):
        run_id = self.env["ons.ai.run"].log_run({
            "task_type": "test_task",
            "requested_model": "test-model-1",
            "actual_model": "test-model-1",
            "input_tokens": 100,
            "output_tokens": 50,
            "total_cost": 0.001,
            "duration_ms": 500,
            "success": True,
            "res_model": "ons.interaction",
            "res_id": self.interaction.id,
            "request_summary": "test input",
            "response_summary": "test output",
        })
        run = self.env["ons.ai.run"].browse(run_id)
        self.assertTrue(run.success)
        self.assertFalse(run.model_mismatch)
        self.assertEqual(run.input_tokens, 100)

    def test_run_log_model_mismatch(self):
        run_id = self.env["ons.ai.run"].log_run({
            "task_type": "test_task",
            "requested_model": "test-model-1",
            "actual_model": "test-model-1-0613",
            "success": True,
        })
        run = self.env["ons.ai.run"].browse(run_id)
        self.assertTrue(run.model_mismatch)

    def test_run_log_truncation(self):
        long_text = "x" * 1000
        run_id = self.env["ons.ai.run"].log_run({
            "task_type": "test_task",
            "requested_model": "test-model-1",
            "success": True,
            "request_summary": long_text,
            "response_summary": long_text,
        })
        run = self.env["ons.ai.run"].browse(run_id)
        self.assertEqual(len(run.request_summary), 500)
        self.assertEqual(len(run.response_summary), 500)

    def test_run_log_failure(self):
        run_id = self.env["ons.ai.run"].log_run({
            "task_type": "test_task",
            "requested_model": "test-model-1",
            "success": False,
            "error_message": "API timeout",
        })
        run = self.env["ons.ai.run"].browse(run_id)
        self.assertFalse(run.success)
        self.assertEqual(run.error_message, "API timeout")

    # ── Budget Tests ────────────────────────────────────────────

    def test_budget_creation(self):
        budget = self.env["ons.ai.budget"].search([], limit=1)
        self.assertTrue(budget)
        self.assertEqual(budget.daily_limit, 50.0)

    def test_budget_check_passes(self):
        """Budget check should pass when under limit."""
        result = self.env["ons.ai.budget"].check_budget()
        self.assertTrue(result)

    def test_budget_check_no_budget_record(self):
        """No budget record should allow all calls."""
        budgets = self.env["ons.ai.budget"].search([])
        budgets.unlink()
        result = self.env["ons.ai.budget"].check_budget()
        self.assertTrue(result)

    # ── Interaction AI Integration Tests ────────────────────────

    def test_interaction_ai_run_count(self):
        self.assertEqual(self.interaction.ai_run_count, 0)
        self.env["ons.ai.run"].log_run({
            "task_type": "intake_classification",
            "requested_model": "test-model-1",
            "success": True,
            "res_model": "ons.interaction",
            "res_id": self.interaction.id,
        })
        self.interaction.invalidate_recordset()
        self.assertEqual(self.interaction.ai_run_count, 1)

    def test_interaction_ai_classify_creates_run(self):
        """AI classify action should create a queued run log entry."""
        # Ensure necessary task/prompt exist
        intake_task = self.env["ons.ai.task"].search([
            ("task_type", "=", "intake_classification"),
        ], limit=1)
        if not intake_task:
            intake_task = self.env["ons.ai.task"].create({
                "task_type": "intake_classification",
                "display_name_custom": "Intake Classify",
                "model_id": self.ai_model.id,
                "temperature": 0.2,
                "max_tokens": 1000,
                "is_enabled": True,
            })
        self.interaction.action_ai_classify()
        runs = self.env["ons.ai.run"].search([
            ("res_model", "=", "ons.interaction"),
            ("res_id", "=", self.interaction.id),
            ("task_type", "=", "intake_classification"),
        ])
        self.assertTrue(runs)
        self.assertFalse(runs[0].success)  # queued, not completed

    def test_interaction_ai_polish_creates_run(self):
        polish_task = self.env["ons.ai.task"].search([
            ("task_type", "=", "description_polish"),
        ], limit=1)
        if not polish_task:
            self.env["ons.ai.task"].create({
                "task_type": "description_polish",
                "display_name_custom": "Polish",
                "model_id": self.ai_model.id,
                "temperature": 0.1,
                "max_tokens": 1000,
                "is_enabled": True,
            })
        self.interaction.action_ai_polish()
        runs = self.env["ons.ai.run"].search([
            ("res_model", "=", "ons.interaction"),
            ("res_id", "=", self.interaction.id),
            ("task_type", "=", "description_polish"),
        ])
        self.assertTrue(runs)

    # ── Case AI Integration Tests ───────────────────────────────

    def test_case_ai_run_count(self):
        self.assertEqual(self.case.ai_run_count, 0)

    def test_case_ai_summarize_creates_run(self):
        summary_task = self.env["ons.ai.task"].search([
            ("task_type", "=", "ticket_summary"),
        ], limit=1)
        if not summary_task:
            self.env["ons.ai.task"].create({
                "task_type": "ticket_summary",
                "display_name_custom": "Summary",
                "model_id": self.ai_model.id,
                "temperature": 0.2,
                "max_tokens": 600,
                "is_enabled": True,
            })
        self.case.action_ai_summarize()
        runs = self.env["ons.ai.run"].search([
            ("res_model", "=", "ons.case"),
            ("res_id", "=", self.case.id),
            ("task_type", "=", "ticket_summary"),
        ])
        self.assertTrue(runs)

    def test_case_ai_customer_report_creates_run(self):
        report_task = self.env["ons.ai.task"].search([
            ("task_type", "=", "customer_report"),
        ], limit=1)
        if not report_task:
            self.env["ons.ai.task"].create({
                "task_type": "customer_report",
                "display_name_custom": "Report",
                "model_id": self.ai_model.id,
                "temperature": 0.4,
                "max_tokens": 500,
                "is_enabled": True,
            })
        self.case.action_ai_customer_report()
        runs = self.env["ons.ai.run"].search([
            ("res_model", "=", "ons.case"),
            ("res_id", "=", self.case.id),
            ("task_type", "=", "customer_report"),
        ])
        self.assertTrue(runs)

    # ── Sanitize for Customer Tests ─────────────────────────────

    def test_sanitize_removes_blocked_words(self):
        text = "The AI generated a summary for this trusted customer"
        result = self.env["ons.interaction"].sanitize_for_customer(text)
        self.assertNotIn("AI", result)
        self.assertNotIn("generated", result)
        self.assertNotIn("trusted", result)

    def test_sanitize_removes_pricing(self):
        text = "The service costs $149 per visit"
        result = self.env["ons.interaction"].sanitize_for_customer(text)
        self.assertNotIn("$149", result)

    def test_sanitize_removes_discord(self):
        text = "Posted on discord channel @agent123 for review"
        result = self.env["ons.interaction"].sanitize_for_customer(text)
        self.assertNotIn("discord", result.lower())

    def test_sanitize_removes_internal_jargon(self):
        text = "Good upsell opportunity, commission is 10%, profit margin looks good"
        result = self.env["ons.interaction"].sanitize_for_customer(text)
        self.assertNotIn("upsell", result.lower())
        self.assertNotIn("commission", result.lower())
        self.assertNotIn("profit", result.lower())
        self.assertNotIn("margin", result.lower())

    def test_sanitize_preserves_normal_text(self):
        text = "We resolved the customer's networking issue successfully"
        result = self.env["ons.interaction"].sanitize_for_customer(text)
        self.assertIn("resolved", result)
        self.assertIn("networking", result)

    def test_sanitize_empty_input(self):
        self.assertEqual(self.env["ons.interaction"].sanitize_for_customer(""), "")
        self.assertEqual(self.env["ons.interaction"].sanitize_for_customer(None), "")

    # ── Deterministic Field Protection Tests ────────────────────

    def test_ai_does_not_own_case_stage(self):
        """AI actions must not write to stage_id — it's deterministic."""
        original_stage = self.case.stage_id
        # Simulate an AI run logging
        self.env["ons.ai.run"].log_run({
            "task_type": "ticket_summary",
            "requested_model": "test-model-1",
            "success": True,
            "res_model": "ons.case",
            "res_id": self.case.id,
        })
        self.case.invalidate_recordset()
        self.assertEqual(self.case.stage_id, original_stage)

    def test_ai_does_not_own_partner(self):
        """AI actions must not write to partner_id — identity resolution owns it."""
        original_partner = self.interaction.partner_id
        self.env["ons.ai.run"].log_run({
            "task_type": "intake_classification",
            "requested_model": "test-model-1",
            "success": True,
            "res_model": "ons.interaction",
            "res_id": self.interaction.id,
        })
        self.interaction.invalidate_recordset()
        self.assertEqual(self.interaction.partner_id, original_partner)

    # ── Seed Data Tests ─────────────────────────────────────────

    def test_seed_prompt_templates_exist(self):
        """All 7 seed prompt templates should exist."""
        codes = [
            "intake_classify", "description_polish", "polish_and_classify",
            "ticket_summary", "customer_report", "coaching_insights", "diarization",
        ]
        for code in codes:
            template = self.env["ons.ai.prompt.template"].search([
                ("code", "=", code),
                ("is_active", "=", True),
            ])
            self.assertTrue(template, f"Missing seed prompt template: {code}")

    def test_seed_tasks_exist(self):
        """All 10 seed task routing entries should exist."""
        types = [
            "intake_classification", "description_polish", "polish_and_classify",
            "transcription", "diarization", "call_grading",
            "coaching_insights", "ticket_summary", "customer_report",
            "copilot_reasoning",
        ]
        for task_type in types:
            task = self.env["ons.ai.task"].search([
                ("task_type", "=", task_type),
            ])
            self.assertTrue(task, f"Missing seed task: {task_type}")
