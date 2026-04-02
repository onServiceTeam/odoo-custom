# 51 — Plan Term Matrix

**Date:** 2026-04-02  
**Prompt:** 6

---

## 1. Plan Terms

| Plan Code | Name | Term (months) | Base Price | Renewable | Notes |
|-----------|------|---------------|------------|-----------|-------|
| `PLAN_6MO` | 6-Month Support Plan | 6 | $249.99 | Yes | Entry-level plan |
| `PLAN_1YR` | 1-Year Support Plan | 12 | $349.99 | Yes | Most popular |
| `PLAN_2YR` | 2-Year Support Plan | 24 | $499.99 | Yes | Best value |

---

## 2. Plan Lifecycle

```
draft → active → expiring_soon → expired
                                ↘ renewed (new plan created)
draft → active → cancelled
```

| State | Condition | Allowed Transitions |
|-------|-----------|---------------------|
| `draft` | Just created, not yet paid/activated | → `active`, → `cancelled` |
| `active` | Paid and current | → `expiring_soon` (auto), → `cancelled` |
| `expiring_soon` | ≤30 days until `end_date` | → `expired` (auto), → `active` (renewed) |
| `expired` | Past `end_date`, not renewed | Terminal |
| `cancelled` | Manually cancelled before term | Terminal |

---

## 3. Date Calculations

```
end_date = start_date + relativedelta(months=term_months)
days_until_expiry = (end_date - today).days
is_expiring_soon = 0 < days_until_expiry <= 30
```

---

## 4. Renewal Rules

1. A new `ons.customer.plan` record is created for the renewal
2. The old plan stays in `expired` state (historical record)
3. The new plan links back to the renewal case via `source_case_id`
4. The new plan's `start_date` = old plan's `end_date` (seamless continuity)
5. Renewal can be same plan or different term (upgrade/downgrade)
6. A plan that is `cancelled` cannot be renewed — a new sale is needed

---

## 5. Add-Ons vs Plans

| Aspect | One-Time Service / Add-On | Support Plan |
|--------|--------------------------|--------------|
| Creates plan record? | No | Yes |
| Has term/expiry? | No | Yes |
| Appears in renewal queue? | No | Yes |
| Tracked on customer profile? | Via case history | As active plan |
| Affects customer segment? | No | Yes (subscriber) |

---

## 6. Pricing Flexibility

Products have a `list_price` (base price) on `product.product`. The VBT can
override the unit price on `ons.case.line` when creating the billing record,
allowing discounts within the min/max range from legacy. The `min_price` and
`max_price` are stored as custom fields on `product.template` for validation
guidance; they are NOT hard constraints in Prompt 6 (they become constraints
when the payment gateway enforces them in a future prompt).
