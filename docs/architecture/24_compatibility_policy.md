# 24 — OCA / Enterprise Compatibility Policy

**Date:** 2026-05-31  
**Purpose:** Define rules for namespace safety, core edit avoidance, OCA module usage, and Enterprise upgrade path.

---

## 1. Namespace Policy

### Module Naming Convention

```
ons_ops_*        — Operations suite modules (custom business logic)
ons_discuss_*    — Discuss/communication extensions (Phase 0)
ons_gif_provider — GIPHY integration
ons_webrtc       — WebRTC health check
discuss_thread_admin — Meta-package (Phase 0 legacy name, frozen)
```

**Rules:**
1. All new modules MUST use `ons_` prefix
2. Module technical names use `snake_case` only
3. No module name may collide with an OCA repo module (check before creating)
4. XML IDs use module-scoped format: `ons_ops_intake.action_interaction_list`
5. Python model names use `ons.` prefix: `ons.interaction`, `ons.call.driver`, `ons.case`
6. Database table names auto-generated as `ons_interaction`, `ons_call_driver`, etc.

### Model Name Registry (Frozen)

| Model | Module | Status |
|-------|--------|--------|
| `ons.interaction` | ons_ops_intake | BUILT |
| `ons.call.driver` | ons_ops_intake | BUILT |
| `ons.case` | ons_ops_cases | PLANNED |
| `ons.case.stage` | ons_ops_cases | PLANNED |
| `ons.session` | ons_ops_cases | PLANNED |
| `ons.dispatch` | ons_ops_dispatch | PLANNED |
| `ons.qa.evaluation` | ons_ops_ai | PLANNED |
| `ons.qa.rule` | ons_ops_ai | PLANNED |
| `ons.threecx.queue` | ons_ops_3cx | PLANNED |
| `ons.threecx.agent` | ons_ops_3cx | PLANNED |
| `ons.callback` | ons_ops_cases | PLANNED |

**Reserved prefixes:**
- `ons.` — all custom models
- `ons_ops_` — all operations modules
- `ons_discuss_` — all Discuss extensions

---

## 2. No-Core-Edit Policy

### Definition

A "core edit" is any modification to files shipped with Odoo Community or Enterprise that are not part of our custom addons directory.

### Rules

1. **NEVER** modify files under `/usr/lib/python3/dist-packages/odoo/` or the Odoo source tree inside the Docker image
2. **NEVER** monkey-patch Odoo models at import time
3. **ALWAYS** extend stock models using `_inherit` in a custom addon
4. **ALWAYS** extend stock views using `<xpath>` inheritance in custom XML
5. **ALWAYS** extend stock JS/CSS using `web.assets_backend` in `__manifest__.py`

### Current Compliance (Verified)

| Module | Core Edits | Method |
|--------|-----------|--------|
| ons_ops_intake | 0 | `_inherit = ['mail.thread', 'mail.activity.mixin']` on new model; extends `res.partner` and `crm.lead` via `_inherit` |
| ons_ops_core | 0 | Security groups via XML data, no model changes to stock |
| ons_ops_shell | 0 | Dashboard via JS client action, menus via XML, SCSS via assets |
| ons_discuss_ui | 0 | Extends `res.users` via `_inherit`; JS/SCSS via assets |
| ons_discuss_threads | 0 | Extends `discuss.channel` via `_inherit` |
| ons_discuss_voice | 0 | Extends `discuss.channel` and RTC session via `_inherit` |
| ons_gif_provider | 0 | Extends `res.config.settings` via `_inherit` |
| ons_webrtc | 0 | HTTP controller only, no model edits |
| discuss_thread_admin | 0 | Meta-package, no code |

**Total core edits: 0** (verified by doc 00 and doc 01 audits)

### Enforcement

- Code review: Any PR touching files outside `/addons/ons_*/` is auto-rejected
- Architecture docs 00 and 01 provide the full audit trail
- This policy extends to future modules: ons_ops_cases, ons_ops_billing, etc.

---

## 3. OCA Module Usage Rules

### Evaluation Matrix

| OCA Module | Repository | Evaluated | Decision | Rationale |
|-----------|-----------|-----------|----------|-----------|
| `helpdesk_mgmt` | oca/helpdesk | Yes | **SKIP** | Our `ons.case` model is more specific to call-center workflow than generic helpdesk |
| `fieldservice` | oca/field-service | Yes | **EVALUATE LATER** | Consider if `ons.dispatch` needs GPS/map features beyond our spec |
| `contract` | oca/contract | Yes | **LATER** | For subscription management when billing module is built |
| `dms` | oca/dms | Yes | **SKIP** | Document management not needed for MVP |
| `knowledge` | oca/knowledge | Yes | **SKIP** | Not needed |
| `phone_validation` | odoo/addons | Yes | **USING** | Already a dependency of ons_ops_intake for `phone_sanitized` |
| `crm` | odoo/addons | Yes | **USING** | Stock CRM, extended with `interaction_id` |
| `account` | odoo/addons | Yes | **WILL USE** | Stock accounting for invoicing when billing module built |

### Rules for Adding OCA Dependencies

1. **License check**: Must be LGPL-3 or AGPL-3 (compatible with Odoo Community LGPL-3)
2. **Version check**: Must support Odoo 19.0 (or be easily portable from 18.0)
3. **Maintenance check**: Must have a recent commit (within 6 months) and active maintainer
4. **Conflict check**: Must not modify models we extend (namespace collision risk)
5. **Upgrade check**: Must not block future Enterprise upgrade path
6. **Approval**: Any OCA dependency requires explicit note in the module's `__manifest__.py` and this document

### Currently Installed OCA Modules

**None.** All dependencies are stock Odoo Community modules: `base`, `mail`, `web`, `contacts`, `crm`, `phone_validation`.

---

## 4. Enterprise Upgrade Path

### Current State: Odoo 19.0 Community

The system runs Odoo Community 19.0-20260324. All custom modules are designed to work with either Community or Enterprise.

### Upgrade Compatibility Checklist

| Concern | Risk | Mitigation |
|---------|------|------------|
| **Module dependencies** | All depend on `base`, `mail`, `crm`, `contacts`, `phone_validation` — all present in Enterprise | ✅ No risk |
| **`crm.lead` extension** | Enterprise adds more fields to `crm.lead` (predictive scoring, etc.) | ✅ No conflict — we only add `interaction_id` |
| **`account.move` usage** | Enterprise has full accounting; Community has limited | ✅ `account` module exists in both; our billing module will use stock API |
| **Security groups** | Enterprise uses `base.group_user` same as Community | ✅ Our groups `implies` `base.group_user` correctly |
| **Web client** | Enterprise has different web client assets | ✅ Our JS/SCSS targets `web.assets_backend`, same bundle name |
| **Studio/Customize** | Enterprise Studio may conflict with custom views | ⚠️ Low risk — document that Studio customizations on our models should be avoided |
| **Helpdesk module** | Enterprise has `helpdesk` (not our model) | ✅ No conflict — we use `ons.case`, not `helpdesk.ticket` |
| **Field Service module** | Enterprise has `industry_fsm` | ⚠️ Potential overlap with `ons.dispatch` — evaluate if dispatch module should bridge instead of duplicate |
| **Subscription module** | Enterprise has `sale_subscription` | ⚠️ Potential overlap — evaluate when billing module built |

### Recommended Upgrade Strategy

1. **Phase 1 (Current):** Stay on Community. Build all `ons_ops_*` modules against Community API.
2. **Phase 2 (Post-MVP):** Evaluate Enterprise for:
   - Full accounting (`account.move` with bank reconciliation)
   - Subscription management (`sale_subscription`)
   - Field service mapping (`industry_fsm` ↔ `ons.dispatch`)
3. **Phase 3 (If upgrading):**
   - Test all 9+ modules on Enterprise in staging
   - Resolve any view inheritance conflicts (xpath may need adjustment)
   - Replace Zoho Books sync with native Odoo Accounting
   - Consider replacing `ons.dispatch` with Enterprise Field Service bridge

### Enterprise-Safe Coding Patterns

```python
# ✅ GOOD: Use _inherit to extend stock models
class ResPartner(models.Model):
    _inherit = "res.partner"
    customer_segment = fields.Selection(...)

# ✅ GOOD: Use xpath to extend stock views  
<record id="view_partner_form_inherit_intake" model="ir.ui.view">
    <field name="inherit_id" ref="base.view_partner_form"/>
    <field name="arch" type="xml">
        <xpath expr="//field[@name='category_id']" position="after">
            <field name="customer_segment"/>
        </xpath>
    </field>
</record>

# ✅ GOOD: Use web.assets_backend for JS/CSS
"assets": {
    "web.assets_backend": [
        "ons_ops_shell/static/src/scss/ops_dashboard.scss",
    ],
}

# ❌ BAD: Direct model replacement
class ResPartner(models.Model):
    _name = "res.partner"  # NEVER replace a stock model

# ❌ BAD: External XML ID override
<record id="base.view_partner_form" model="ir.ui.view">  # NEVER use stock XML ID
```

---

## 5. Version Pinning

### Odoo Version

```
Odoo: 19.0-20260324 (Docker image: odoo:19.0)
PostgreSQL: 18 (Docker image: postgres:18)
Python: 3.12+ (from Odoo Docker image)
```

### Custom Module Versioning

All custom modules follow Odoo's versioning convention: `{odoo_version}.{module_version}`

| Module | Current Version | Status |
|--------|----------------|--------|
| ons_ops_core | 19.0.1.0.0 | Stable |
| ons_ops_shell | 19.0.1.0.0 | Stable |
| ons_ops_intake | 19.0.1.0.0 | Stable (phone fix = 19.0.1.0.1 after this commit) |
| ons_discuss_ui | 19.0.1.0.0 | Stable |
| ons_discuss_threads | 19.0.1.0.0 | Stable |
| ons_discuss_voice | 19.0.1.0.0 | Stable |
| ons_gif_provider | 19.0.1.0.0 | Stable |
| ons_webrtc | 19.0.1.0.0 | Stable |
| discuss_thread_admin | 19.0.6.0.0 | Stable (meta-package) |

### Version Bump Policy

- **Patch** (x.x.x.x.**1**): Bug fixes, no field changes
- **Minor** (x.x.x.**1**.0): New fields added (backward compatible)
- **Major** (x.x.**1**.0.0): Breaking changes (requires migration script)
- **Odoo version** (19.0 → 20.0): Full module migration, new `__manifest__.py` version

---

## 6. Migration Script Policy

### When Required

A migration script (`upgrades/{version}/pre-migrate.py` or `post-migrate.py`) is REQUIRED when:
1. Renaming a field
2. Changing a field type
3. Removing a field
4. Changing a unique constraint
5. Altering enum values in a Selection field (removing values)
6. Changing a model name

### When NOT Required

No migration script needed for:
1. Adding a new field (Odoo handles this automatically)
2. Adding new enum values to a Selection (additive change)
3. Adding a new model
4. Changing computed field logic (no database change)
5. View changes (XML only, no data migration)

### Current Migration Scripts

```
ons_ops_core/upgrades/     — exists (empty placeholder)
ons_ops_shell/upgrades/    — exists (empty placeholder)
ons_ops_intake/upgrades/   — exists (empty placeholder)
```

No active migrations needed yet — all changes so far are additive.
