# 52 — Future Mapping to OCA or Enterprise

**Date:** 2026-04-02  
**Prompt:** 6

---

## 1. Purpose

Document how the custom billing models in `ons_ops_billing` can later map to
OCA or Odoo Enterprise modules without a rewrite.

---

## 2. OCA Contract / Subscription Mapping

| Custom Model | OCA Module | Mapping Strategy |
|-------------|------------|------------------|
| `ons.customer.plan` | `contract` (OCA) | Plan → Contract with recurring invoice line |
| `ons.case.line` | — | No OCA equivalent; stays custom |
| `product.product` extensions | — | Already stock-compatible |
| `account.move` | — | Already stock |

**Migration path if OCA adopted:**
1. Install `contract` module
2. Create migration script that converts `ons.customer.plan` records to `contract.contract`
3. Map `term_months` to contract line recurrence
4. Keep `ons.case.line` as-is (it serves a different purpose than contract lines)
5. Custom plan fields (`plan_code`, `stripe_subscription_id`) move to contract extensions

---

## 3. Enterprise Subscription Mapping

| Custom Model | Enterprise Module | Mapping Strategy |
|-------------|-------------------|------------------|
| `ons.customer.plan` | `sale.subscription` (Enterprise) | Plan → Subscription |
| Plan terms | Subscription template + pricing | Direct mapping |
| Renewal | Subscription renewal workflow | Native replacement |
| `ons.case.line` | — | No equivalent; stays custom |

**Migration path if Enterprise adopted:**
1. Install `sale_subscription`
2. Create subscription templates from plan products
3. Migrate `ons.customer.plan` → `sale.subscription`
4. Replace renewal queue with native subscription dashboard
5. Keep `ons.case.line` for case-specific billing

---

## 4. Design Decisions That Preserve Compatibility

1. **Products are stock `product.product`** — no custom product model
2. **Invoices are stock `account.move`** — no custom invoice model
3. **Plan is a separate model** — not embedded in cases or partners
4. **Plan has explicit start/end dates** — maps to any contract/subscription system
5. **Plan has `state` field** — matches lifecycle patterns of OCA/Enterprise
6. **No tight coupling to Stripe** — `stripe_subscription_id` is a reference field, not a dependency
7. **Case lines are case-specific** — they complement, not replace, invoice lines

---

## 5. Risk Assessment

| Risk | Mitigation |
|------|-----------|
| OCA `contract` has different field names | Migration script handles mapping |
| Enterprise `sale.subscription` requires `sale` module | `sale` can be installed alongside |
| Custom plan renewal logic conflicts with native | Disable custom cron, enable native |
| `ons.case.line` redundant with SO lines | Keep both; case lines are pre-invoice |

---

## 6. Recommendation

Stay with custom `ons.customer.plan` for now. It is thin, explicit, and easy
to migrate. If the business later adopts OCA contracts or Enterprise
subscriptions, the migration is a one-time script, not a rewrite.
