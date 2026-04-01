# ons_discuss_ui

**Version:** 19.0.1.0.0  
**License:** LGPL-3  
**Depends:** mail  

## Purpose

Provides Discord/Slack-style UI enhancements for Odoo Discuss:
- Dark + light theme SCSS overrides
- Work status dropdown (emoji + text, replacing stock IM status)
- Tab title unread message counter
- Configurable sidebar category labels (Channels, Chats)
- Option to hide "Looking for Help" livechat category
- IM status lockdown (presence-only, no manual override)

## Configuration

Settings > Discuss section:
- **Only Admins Can Delete Threads** — restrict thread deletion to admin users
- **Auto-Cleanup Empty Group Chats** — auto-delete groups when last member leaves
- **Channels/Chats Label** — custom sidebar category names
- **Hide Looking for Help** — hide livechat category

## Config Parameter Keys

Uses `discuss_thread_admin.*` prefix for backward compatibility with the
original monolith addon. These keys have existing values in `ir.config_parameter`
and renaming requires a data migration.

## Upgrade Notes

| Risk | Component | Detail |
|------|-----------|--------|
| MEDIUM | SCSS | Discord theme overrides many `.o_Discuss*` selectors — may break on Discuss UI refactors |
| MEDIUM | JS patches | `Store.prototype`, `DiscussAppCategory.prototype` — fragile if Odoo restructures these |
| LOW | XML views | `res_config_settings_views.xml` inherits stock settings view via xpath |
| LOW | Controllers | `/discuss/set_work_status`, `/mail/set_manual_im_status` — custom routes unlikely to conflict |

## Testing

```bash
docker exec odoo-web odoo -d test_db -i ons_discuss_ui --test-enable --stop-after-init --no-http
```
