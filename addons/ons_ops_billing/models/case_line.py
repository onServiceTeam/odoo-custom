# -*- coding: utf-8 -*-
from odoo import api, fields, models


class CaseLine(models.Model):
    _name = "ons.case.line"
    _description = "Case Billing Line"
    _order = "sequence, id"

    case_id = fields.Many2one(
        "ons.case",
        required=True,
        ondelete="cascade",
        index=True,
    )
    product_id = fields.Many2one(
        "product.product",
        string="Product",
        required=True,
    )
    description = fields.Text(string="Description")
    sequence = fields.Integer(default=10)
    quantity = fields.Float(default=1.0, digits=(10, 2))
    unit_price = fields.Float(string="Unit Price", digits=(10, 2))
    subtotal = fields.Float(
        compute="_compute_subtotal",
        store=True,
        digits=(10, 2),
    )

    @api.depends("quantity", "unit_price")
    def _compute_subtotal(self):
        for rec in self:
            rec.subtotal = rec.quantity * rec.unit_price

    @api.onchange("product_id")
    def _onchange_product_id(self):
        if self.product_id:
            self.unit_price = self.product_id.list_price
            if not self.description:
                self.description = self.product_id.name
