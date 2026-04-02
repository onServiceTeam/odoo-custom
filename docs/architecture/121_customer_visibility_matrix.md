# 121 — Customer Visibility Matrix

Portal users see **only** their own records, filtered by
`partner_id child_of commercial_partner_id`.

## Field visibility by model

### ons.case

| Field | Visible | Display |
|-------|---------|---------|
| name | yes | Case reference |
| stage_id.name | yes | Friendly stage label |
| is_closed | yes | Terminal status badge |
| is_won | yes | Success indicator |
| issue_description | yes | What was reported |
| summary | yes (if customer_report absent) | Sanitised summary |
| customer_report | yes | AI customer-facing report |
| next_action | yes | What happens next |
| next_action_at | yes | Scheduled date |
| create_date | yes | When opened |
| write_date | yes | Last update |
| amount_total | yes | Total billed |
| payment_status | yes | Payment state badge |
| case_line_ids | yes | Billing line items |
| intake_agent_id.name | yes | Agent display name only |
| assigned_tech_id.name | yes | Tech display name only |
| hours_in_pipeline | **no** | Internal metric |
| aging_bucket | **no** | Internal metric |
| ai_summary | **no** | Internal AI advisory |

### ons.case.line

| Field | Visible | Display |
|-------|---------|---------|
| product_id.name | yes | Product / service name |
| description | yes | Line description |
| quantity | yes | Qty |
| unit_price | yes | Price |
| subtotal | yes | Line subtotal |

### ons.customer.plan

| Field | Visible | Display |
|-------|---------|---------|
| product_id.name | yes | Plan name |
| plan_code | yes | Code |
| amount | yes | Monthly / term amount |
| term_months | yes | Duration |
| start_date | yes | Start |
| end_date | yes | End / renewal date |
| state | yes | active / expiring / expired / cancelled |
| days_until_expiry | yes | Countdown |
| is_expiring_soon | yes | Warning badge |
| stripe_subscription_id | **no** | Internal |

### ons.dispatch

| Field | Visible | Display |
|-------|---------|---------|
| name | yes | Reference |
| title | yes | Brief description |
| description | yes | Detailed description |
| dispatch_status | yes | Friendly status label |
| is_terminal | yes | Done indicator |
| scheduled_start | yes | When the tech arrives |
| scheduled_end | yes | When the window ends |
| assigned_worker_name | yes | Tech name |
| contact_phone | yes | Customer's own phone |
| street, city, zip | yes | Customer's own address |
| checklist_progress | yes | % complete |
| confirmed_at | yes | Confirmation timestamp |
| completed_at | yes | Completion timestamp |
| budget | **no** | Internal pricing |
| special_instructions | **no** | Internal notes |

### ons.contact.consent

| Field | Visible | Display |
|-------|---------|---------|
| channel | yes | email / sms |
| scope | yes | marketing / operational |
| status | yes | active / pending / revoked |
| opted_in_at | yes | When opted in |
| opted_out_at | yes | When opted out |
| captured_by_id | **no** | Internal |
| capture_source | **no** | Internal |

## Record-level rules

| Model | Rule | Domain |
|-------|------|--------|
| ons.case | portal_case_own | `[('partner_id','child_of',[user.commercial_partner_id.id])]` |
| ons.case.line | portal_case_line_own | `[('case_id.partner_id','child_of',[user.commercial_partner_id.id])]` |
| ons.customer.plan | portal_plan_own | `[('partner_id','child_of',[user.commercial_partner_id.id])]` |
| ons.dispatch | portal_dispatch_own | `[('partner_id','child_of',[user.commercial_partner_id.id])]` |
| ons.contact.consent | portal_consent_own | `[('partner_id','child_of',[user.commercial_partner_id.id])]` |
