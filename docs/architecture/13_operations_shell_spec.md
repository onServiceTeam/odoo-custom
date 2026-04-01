# 13 — Operations Shell Spec

**Date:** 2026-04-01  
**Module:** `ons_ops_shell`  
**Phase:** 3 (built after core models, before business modules)  

---

## Design Philosophy

The team currently uses a focused sidecar app with a left-nav cockpit. They should
NOT be forced into navigating generic Odoo menus to find their workflows.

The shell provides:
1. A custom left-side navigation replacing default Odoo menu clutter
2. A focused home/dashboard screen
3. Role-based visibility (agents see different nav than managers)
4. Quick-access actions (new intake, search customer, etc.)

---

## Navigation Structure

```
┌─────────────────────────────────────────────┐
│  🏠 onService Operations Center             │
├─────────────────────────────────────────────┤
│                                             │
│  📞 Intake          ← New call form         │
│  👥 Customers       ← Partner list/search   │
│  📋 Active Cases    ← Kanban board          │
│  💼 Leads           ← CRM pipeline          │
│  🔧 Sessions        ← Session tracker       │
│  🚛 Dispatch        ← Dispatch queue        │
│  📱 Calls           ← 3CX call history      │
│  💬 Discuss         ← Odoo Discuss          │
│  📧 Inbox           ← Shared inbox          │
│  📊 Reports         ← Dashboards            │
│  ─────────────────                          │
│  ⚙️ Admin            ← Settings, config     │
│  👤 My Performance  ← Agent dashboard       │
│  👥 Team            ← Manager dashboard     │
│  🎯 QA Center       ← QA command center     │
│                                             │
└─────────────────────────────────────────────┘
```

---

## Role-Based Visibility

| Nav Item | Agent | Manager | Admin |
|----------|-------|---------|-------|
| Intake | ✅ | ✅ | ✅ |
| Customers | ✅ | ✅ | ✅ |
| Active Cases | ✅ | ✅ | ✅ |
| Leads | ✅ | ✅ | ✅ |
| Sessions | ✅ | ✅ | ✅ |
| Dispatch | ❌ | ✅ | ✅ |
| Calls | ✅ | ✅ | ✅ |
| Discuss | ✅ | ✅ | ✅ |
| Inbox | ✅ | ✅ | ✅ |
| Reports | ❌ | ✅ | ✅ |
| Admin | ❌ | ❌ | ✅ |
| My Performance | ✅ | ✅ | ✅ |
| Team | ❌ | ✅ | ✅ |
| QA Center | ❌ | ✅ | ✅ |

---

## Implementation Strategy

### Option A: Custom WebClient (Owl Component)
- Override the `WebClient` to replace the default nav
- Use Odoo `registry` for menu items
- Custom `ActionManager` for the cockpit
- **Pro:** Full control. **Con:** Fragile on Odoo upgrades.

### Option B: Menu Cleanup + Custom Dashboard (Recommended)
- Use `menuitem` XML to create a focused top-level "Operations" menu
- Hide/resequence stock menus via `ir.ui.menu` records
- Create a custom dashboard as the home action
- Use `ir.actions.client` for custom JS views
- **Pro:** Uses standard Odoo patterns. **Con:** Less custom look.

### Option C: Hybrid
- Keep standard Odoo chrome but inject a custom sidebar component
- Use `@web/core/browser/router` hooks to add the cockpit nav
- **Pro:** Best of both. **Con:** Medium upgrade risk.

**Recommendation: Option B for MVP, evolve to C if needed.**

The standard Odoo menu system is sufficient for initial deployment. The team
gets a focused "Operations" section without the fragility of custom chrome.
The existing `ons_discuss_ui` already proves we can customize the look
significantly via SCSS alone.

---

## Home Dashboard Widgets

The home screen (accessed via the main "Operations" menu) should show:

| Widget | Data Source | Refresh |
|--------|-----------|---------|
| Today's Call Count | ons.interaction (today, phone) | 60s |
| Open Cases | ons.case (not closed) | 60s |
| My Active Sessions | ons.session (my, not completed) | 60s |
| Pending Dispatch | ons.dispatch (not completed) | 60s |
| Unread Inbox | mail.message (unread) | 30s |
| Revenue Today | account.payment (today) | 5min |
| QA Pending Review | ons.qa.evaluation (pending) | 5min |
| 3CX Queue Status | ons.threecx.queue (active) | 30s |

---

## Action Shortcuts

Quick-access buttons on the home dashboard:

| Action | Target |
|--------|--------|
| New Intake | ons.interaction form (intake wizard) |
| Search Customer | res.partner search |
| My Cases | ons.case tree (assigned to me) |
| Today's Calls | ons.interaction tree (today, phone) |

---

## Upgrade Notes

| Risk | Component | Detail |
|------|-----------|--------|
| LOW | Menu XML | Standard `ir.ui.menu` records — stable across versions |
| MEDIUM | Dashboard JS | Client action with Owl components — monitor @web imports |
| LOW | SCSS | Builds on existing ons_discuss_ui theme |
| LOW | Security | Uses standard Odoo groups for visibility |
