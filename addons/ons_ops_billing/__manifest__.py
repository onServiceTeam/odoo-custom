# -*- coding: utf-8 -*-
{
    "name": "onService Operations — Billing",
    "version": "19.0.1.0.0",
    "category": "Services",
    "summary": "Products, billing backbone, customer plans, and renewal tracking",
    "description": """
onService Operations — Billing
================================

Internal billing structure for the onService Operations Center.

* **Product catalog** — Service products seeded to match legacy
  ``payment_products`` with categories: one-time service, support plan,
  add-on.  Extensions for min/max price and subscription metadata.
* **ons.case.line** — Links products to cases with quantity, unit price,
  and computed subtotals.
* **Case billing extension** — Payment status, invoice link, no-charge
  and manual payment tracking on ``ons.case``.
* **ons.customer.plan** — Customer subscription/plan lifecycle with
  start/end dates, renewal tracking, expiry alerts, and churn management.
* **Renewal work queue** — Views for plans expiring soon, expired,
  active, and cancelled.

Upgrade Safety
--------------
* Uses stock ``product.product`` and ``account.move`` — no custom
  replacements for native accounting objects.
* ``ons.case.line`` and ``ons.customer.plan`` are additive custom models.
* ``ons.case`` extensions add fields only — no stock model changes.
* ``product.template`` extension adds optional price range fields.
* Design is OCA-contract-friendly and Enterprise-subscription-friendly
  for future adoption (see ``52_future_mapping_to_oca_or_enterprise.md``).
    """,
    "author": "OnService",
    "website": "https://team.onservice.us",
    "license": "LGPL-3",
    "depends": [
        "ons_ops_cases",
        "account",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/product_category_data.xml",
        "data/product_data.xml",
        "data/cron_data.xml",
        "views/product_views.xml",
        "views/case_line_views.xml",
        "views/case_billing_views.xml",
        "views/customer_plan_views.xml",
        "views/ops_billing_menus.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
