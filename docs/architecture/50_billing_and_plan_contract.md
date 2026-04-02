# 50 — Billing and Plan Contract

**Date:** 2026-04-02  
**Prompt:** 6  
**Addon:** `ons_ops_billing`

---

## 1. Overview

This contract defines how the billing backbone connects cases to products,
invoices, payments, customer plans, and renewals inside Odoo Community 19.

**Design principles:**
- Use native `product.product` and `account.move` where they fit
- Add thin bridge models for business logic Odoo stock doesn't cover
- Keep the design Enterprise- and OCA-friendly for later adoption
- Stripe/Zoho integrations are NOT built in this prompt — only the internal
  structure that a future gateway prompt can connect to

---

## 2. Product Categories

Legacy `payment_products.category` maps to Odoo as follows:

| Legacy Category | Odoo Product Category | `product_type` | Notes |
|-----------------|----------------------|-----------------|-------|
| `paid_fix` | One-Time Service | `service` | Standard Fix, Advanced Repair, Custom Fix |
| `downsell` | One-Time Service | `service` | Quick Fix (discounted tier) |
| `subscription` | Support Plan | `service` | 6-month, 1-year, 2-year plans |
| `addon` | Add-On | `service` | Browser Guard, Data Backup, adjustments |
| `refund` | (not a product) | — | Handled via credit notes on `account.move` |

All products are type `service` (not `consu` or `product`) because onService
delivers remote/onsite tech support, not physical goods.

---

## 3. Product Catalog (Seed Data)

| Code | Name | Price | Category | Subscription? | Term (months) |
|------|------|-------|----------|---------------|---------------|
| `QUICK_FIX` | Quick Fix | 49.99 | One-Time Service | No | — |
| `STANDARD_FIX` | Standard Fix | 129.99 | One-Time Service | No | — |
| `ADVANCED_REPAIR` | Advanced Repair | 149.99 | One-Time Service | No | — |
| `CUSTOM_FIX` | Custom Fix | 0.00 | One-Time Service | No | — |
| `PLAN_6MO` | 6-Month Support Plan | 249.99 | Support Plan | Yes | 6 |
| `PLAN_1YR` | 1-Year Support Plan | 349.99 | Support Plan | Yes | 12 |
| `PLAN_2YR` | 2-Year Support Plan | 499.99 | Support Plan | Yes | 24 |
| `BROWSER_GUARD` | Browser Guard | 49.99 | Add-On | No | — |
| `DATA_BACKUP` | Data Backup Service | 79.99 | Add-On | No | — |
| `ADDITIONAL_PAYMENT` | Additional Payment | 0.00 | Add-On | No | — |
| `SMALL_ADJUSTMENT` | Small Adjustment | 0.00 | Add-On | No | — |

Products with `0.00` price use variable pricing set at invoice time.

---

## 4. How a Case Becomes Billable

```
repair_in_progress → ready_for_verification → billing_in_progress → paid → closed_won
```

1. Tech completes repair → stage moves to `ready_for_verification`
2. VBT (billing_agent_id) takes over → stage becomes `billing_in_progress`
3. VBT selects product(s) on the case and creates an invoice
4. Invoice sent to customer → `payment_status = invoice_sent`
5. Payment received → `payment_status = paid`
6. Case stage advances to `paid` then `closed_won`

**Special flows:**
- **No Charge:** Subscriber/warranty/goodwill — skip invoice, mark `no_charge`
- **Manual Payment:** Check, cash, Zelle, etc. — record directly, no Stripe
- **Partial Payment:** Partial amount received, balance pending — `partial`

---

## 5. What Lives in Native Odoo vs Custom Bridge

| Concept | Where | Why |
|---------|-------|-----|
| Product catalog | `product.product` | Stock Odoo, good fit |
| Product categories | `product.category` | Stock Odoo |
| Invoice | `account.move` | Stock Odoo accounting |
| Invoice lines | `account.move.line` | Stock Odoo |
| Payment state | `account.move.payment_state` | Stock Odoo |
| Case → product link | `ons.case.line` (NEW) | Need multi-product per case with qty/price |
| Case → invoice link | `ons.case` extension | Many2one to `account.move` |
| Case payment status | `ons.case` extension | Business-level status beyond Odoo's |
| Customer plan | `ons.customer.plan` (NEW) | No stock subscription in Community |
| Plan renewal tracking | `ons.customer.plan` | Renewal dates, expiry, churn |

---

## 6. Custom Models

### `ons.case.line` — Case Billing Line
Links a product to a case with quantity and unit price.

| Field | Type | Notes |
|-------|------|-------|
| case_id | Many2one → ons.case | Required |
| product_id | Many2one → product.product | Required |
| quantity | Float | Default 1.0 |
| unit_price | Float | From product list_price, editable |
| subtotal | Float (computed) | qty × unit_price |
| description | Text | Optional override |

### `ons.customer.plan` — Customer Subscription Plan
Represents a customer's active/expired/cancelled support plan.

| Field | Type | Notes |
|-------|------|-------|
| partner_id | Many2one → res.partner | Required |
| product_id | Many2one → product.product | Plan product |
| plan_code | Char | e.g., PLAN_1YR |
| state | Selection | draft / active / expiring_soon / expired / cancelled |
| start_date | Date | When the plan started |
| end_date | Date (computed) | start_date + term months |
| term_months | Integer | 6, 12, or 24 |
| amount | Float | Total plan price |
| is_renewable | Boolean (computed) | Not cancelled |
| days_until_expiry | Integer (computed) | |
| is_expiring_soon | Boolean (computed) | ≤ 30 days |
| renewal_case_id | Many2one → ons.case | Case that renewed this plan |
| source_case_id | Many2one → ons.case | Case that created this plan |
| source_invoice_id | Many2one → account.move | |
| stripe_subscription_id | Char | For migration/sync reference |

---

## 7. Case Extensions for Billing

New fields on `ons.case`:

| Field | Type | Notes |
|-------|------|-------|
| case_line_ids | One2many → ons.case.line | Products on this case |
| invoice_id | Many2one → account.move | Linked invoice |
| payment_status | Selection | pending / invoice_sent / paid / partial / no_charge / manual / declined / refunded / disputed |
| payment_amount | Float | Actual amount collected |
| no_charge_reason | Selection | subscriber / warranty / goodwill / followup / other |
| manual_payment_method | Selection | check / cash / wire / zelle / venmo / paypal / other |
| is_billable | Boolean (computed) | Has case lines and not closed_lost |
| amount_total | Float (computed) | Sum of case lines |
| plan_id | Many2one → ons.customer.plan | If this case is servicing a plan customer |

---

## 8. Invariants

1. A case may have zero or many case lines.
2. `payment_status` defaults to `pending`.
3. `no_charge` requires `no_charge_reason`.
4. `manual` payment requires `manual_payment_method`.
5. Invoice can only be created when case has at least one case line.
6. Plan creation requires a subscription-category product.
7. `end_date` is always `start_date + term_months`.
8. Plans in `expiring_soon` state: `end_date` within 30 days of today.
9. A plan can only be renewed if `state != cancelled`.
10. Case `amount_total` must match invoice total when invoice exists.

---

## 9. Payment Status State Machine

```
pending → invoice_sent → paid
pending → invoice_sent → partial → paid
pending → no_charge
pending → manual → paid
pending → declined
paid → refunded
paid → disputed
partial → refunded
```

---

## 10. Future Integration Points

- **Prompt 7 (3CX):** No billing impact
- **Prompt 8 (Dispatch):** Onsite cases may have different pricing
- **Prompt 14 (Migration):** `payment_products.odoo_product_id` maps to seeded products
- **Stripe gateway:** Future addon connects to `ons.customer.plan.stripe_subscription_id`
- **OCA contract:** `ons.customer.plan` maps cleanly to OCA contract model
- **Enterprise subscriptions:** `ons.customer.plan` can be replaced or bridged
