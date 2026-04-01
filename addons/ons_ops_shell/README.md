# onService Operations — Shell

Operations center navigation, dashboard, and menu framework.

## What This Module Does

- Adds a top-level **"Operations"** application menu (sequence 3)
- Provides a **home dashboard** with live KPI cards and quick-action buttons
- Creates **section menus** that future `ons_ops_*` modules populate:
  - Intake & CRM (Customers, Pipeline)
  - Communication (Discuss)
  - Management (manager+ only)
  - Configuration (admin only)

## Menu Architecture

```
Operations (app root, sequence 3)
├── Dashboard                    → ons_ops_shell.dashboard (Owl component)
├── Intake & CRM
│   ├── Customers                → contacts.action_contacts
│   └── Pipeline                 → crm.crm_lead_action_pipeline
├── Communication
│   └── Discuss                  → mail.action_discuss
├── Management                   → (manager+, populated by future modules)
└── Configuration                → (admin only, populated by future modules)
```

## Extending the Menu

Future modules add leaf items by referencing section parents:

```xml
<!-- In ons_ops_intake/views/menus.xml -->
<menuitem
    id="menu_ops_call_intake"
    name="Call Intake"
    parent="ons_ops_shell.menu_ops_intake_section"
    action="action_intake_form"
    sequence="5"
/>
```

## Dashboard KPIs

| Card | Data Source | Click Action |
|------|-----------|-------------|
| Customers | `res.partner` WHERE customer_rank > 0 | Contacts list |
| Open Leads | `crm.lead` count | CRM Pipeline |
| My Activities | `mail.activity` WHERE user_id = me | Activity list |
| Discuss | N/A (navigation link) | Odoo Discuss |

## Upgrade Safety

| Concern | Status |
|---------|--------|
| Stock menu changes | None — additive only |
| Stock view changes | None |
| Dashboard JS | Owl component — monitor `@web` imports on upgrades |
| Enterprise conflicts | None — no Enterprise model namespaces used |
| OCA compatibility | Full — standard menu/action patterns |

## Depends

- `ons_ops_core` (security groups)
- `contacts` (Customers menu)
- `crm` (Pipeline menu)
- `mail` (Discuss menu + activity counts)
