# 120 — Customer Portal Contract

## Scope

`ons_ops_portal` provides an authenticated customer self-service area
under `/my/*`.  It extends the stock Odoo portal (already installed) with
pages for service cases, subscription plans, onsite dispatches, and
communication preferences (consent).

The legacy middleware has **no** customer-facing portal — all views were
internal.  This is new functionality built on the Odoo models already in
place.

## What customers can see

| Data | Source Model | Route | Notes |
|------|-------------|-------|-------|
| Service cases | `ons.case` | `/my/cases`, `/my/cases/<id>` | Stage, description, next action, billing lines, amount, report |
| Billing lines | `ons.case.line` | embedded in case detail | Product, qty, unit price, subtotal |
| Customer report | `ons.case.customer_report` (AI field) | embedded in case detail | Sanitised AI-generated text; shown if populated |
| Subscription plans | `ons.customer.plan` | `/my/plans`, `/my/plans/<id>` | State, term, dates, renewal window |
| Onsite dispatches | `ons.dispatch` | `/my/dispatches`, `/my/dispatches/<id>` | Status, schedule, worker, checklist % |
| Invoices | `account.move` | `/my/invoices` (stock) | Already provided by `account` portal |
| Consent prefs | `ons.contact.consent` | `/my/consent` | Opt-in / opt-out self-service |

## What customers can do

| Action | Mechanism |
|--------|-----------|
| View case status & history | Read-only portal page |
| View service report | Embedded AI customer_report text |
| View plan status & renewal window | Read-only portal page |
| View dispatch schedule & progress | Read-only portal page |
| Manage consent preferences | Toggle opt-in / opt-out via form POST |
| Request callback | Creates `ons.interaction` with type=callback |

## What customers cannot do

- Create or modify cases
- Change billing or payment data
- See internal fields: aging_bucket, hours_in_pipeline, AI-internal summary, QA evaluations
- See other customers' records
- View agent/technician user details beyond display name
- Modify dispatch scheduling or assignment
- Access CRM leads (leads are internal)

## Security model

Every portal-exposed model is restricted by `ir.rule`:
```
domain_force = [('partner_id', 'child_of', [user.commercial_partner_id.id])]
```
For `ons.case.line` access is indirect through the parent case ACL.

Portal users belong to `base.group_portal` — the stock Odoo portal group.
No custom portal group is created.

## portal.mixin integration

Three models gain `portal.mixin`:
- `ons.case` → `access_url = /my/cases/<id>`
- `ons.customer.plan` → `access_url = /my/plans/<id>`
- `ons.dispatch` → `access_url = /my/dispatches/<id>`

This provides `access_token` for shareable links and `get_portal_url()` for
email notifications.

## Home page badges

The `/my` home gains three counter badges under `portal_service_category`:
- **Cases** (open case count)
- **Plans** (active plan count)
- **Dispatches** (pending dispatch count)

## Dependencies

`portal`, `website`, `ons_ops_cases`, `ons_ops_billing`,
`ons_ops_dispatch`, `ons_ops_comms`, `ons_ops_crm`
