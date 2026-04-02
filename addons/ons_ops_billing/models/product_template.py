# -*- coding: utf-8 -*-
from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    # ── onService extensions ────────────────────────────────────────
    ons_product_code = fields.Char(
        string="onService Code",
        index=True,
        help="Legacy product_code from payment_products, e.g. QUICK_FIX",
    )
    ons_category = fields.Selection(
        [
            ("one_time", "One-Time Service"),
            ("subscription", "Support Plan"),
            ("addon", "Add-On"),
        ],
        string="onService Category",
        index=True,
    )
    ons_is_subscription = fields.Boolean(string="Is Subscription Plan")
    ons_subscription_months = fields.Integer(
        string="Plan Term (months)",
        help="6, 12, or 24 for subscription plans",
    )
    ons_min_price = fields.Float(
        string="Min Price",
        digits=(10, 2),
        help="Discount floor — guidance for billing agents",
    )
    ons_max_price = fields.Float(
        string="Max Price",
        digits=(10, 2),
        help="Premium ceiling — guidance for billing agents",
    )
