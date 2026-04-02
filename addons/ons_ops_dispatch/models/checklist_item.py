# -*- coding: utf-8 -*-
from odoo import fields, models


class ChecklistItem(models.Model):
    _name = "ons.dispatch.checklist.item"
    _description = "Dispatch Checklist Item"
    _order = "sequence, id"

    dispatch_id = fields.Many2one(
        "ons.dispatch",
        required=True,
        ondelete="cascade",
        index=True,
    )
    checklist_code = fields.Char(required=True, index=True)
    name = fields.Char(string="Item", required=True)
    sequence = fields.Integer(default=10)
    is_required = fields.Boolean(default=False)
    completed = fields.Boolean(default=False)
    completed_by = fields.Many2one("res.users")
    completed_at = fields.Datetime()
    notes = fields.Text()

    _item_unique = models.UniqueIndex(
        "(dispatch_id, checklist_code)",
        "Each checklist item can only appear once per dispatch.",
    )

    def action_toggle_complete(self):
        self.ensure_one()
        if self.completed:
            self.write({"completed": False, "completed_by": False, "completed_at": False})
        else:
            self.write({
                "completed": True,
                "completed_by": self.env.uid,
                "completed_at": fields.Datetime.now(),
            })
