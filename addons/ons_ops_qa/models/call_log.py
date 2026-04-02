from odoo import api, fields, models


class CallLog(models.Model):
    _inherit = "ons.call.log"

    qa_result_ids = fields.One2many("ons.qa.result", "call_log_id", string="QA Results")
    qa_result_count = fields.Integer(compute="_compute_qa_result_count")
    qa_latest_score = fields.Float(
        digits=(5, 2), compute="_compute_qa_result_count", string="Latest QA Score",
    )

    @api.depends("qa_result_ids", "qa_result_ids.effective_score")
    def _compute_qa_result_count(self):
        for rec in self:
            results = rec.qa_result_ids
            rec.qa_result_count = len(results)
            if results:
                rec.qa_latest_score = results[0].effective_score
            else:
                rec.qa_latest_score = 0.0

    def action_view_qa_results(self):
        """Open QA results for this call log."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "QA Results",
            "res_model": "ons.qa.result",
            "view_mode": "list,form",
            "domain": [("call_log_id", "=", self.id)],
            "context": {"default_call_log_id": self.id},
        }
