# ons_discuss_threads

**Version:** 19.0.1.0.0  
**License:** LGPL-3  
**Depends:** mail, ons_discuss_ui  

## Purpose

Thread and channel administration features for Odoo Discuss:
- Admin-only thread deletion with configurable policy
- Kick member from channel (admin)
- Hard-delete messages permanently (admin)
- Drag-and-drop channel reorder via `sequence` field
- Leave-channel warning when last member
- Customer intake model (`discuss.intake`) with auto-thread creation
- Channel info endpoint (member list, message count)

## Models

- **discuss.channel** (inherited) — adds `sequence` field, auto-cleanup on member leave
- **discuss.intake** (new) — customer intake records that auto-create sub-channels

## Routes

| Route | Auth | Purpose |
|-------|------|---------|
| `/discuss/channel/sub_channel/delete` | user | Delete thread (admin-controlled) |
| `/discuss/channel/sub_channel/thread_settings` | user | Get admin policy settings |
| `/discuss/channel/admin/kick_member` | admin | Remove member from channel |
| `/discuss/channel/admin/hard_delete_message` | admin | Permanently delete message |
| `/discuss/channel/admin/channel_info` | admin | Get channel member/message info |
| `/discuss/channel/admin/pre_leave_check` | user | Check if leaving would auto-delete |
| `/discuss/channel/admin/reorder` | admin | Set channel order via sequence |
| `/discuss/intake/create` | user | Create intake + auto-thread |

## Upgrade Notes

| Risk | Component | Detail |
|------|-----------|--------|
| MEDIUM | JS patches | 7 JS files patching Thread, Store, Composer, DiscussAppCategory |
| MEDIUM | `discuss.channel._action_unfollow` | Override — may break if stock signature changes |
| LOW | `discuss.intake` model | New model, no collision risk |
| LOW | XML views | Admin menus and tree views via standard inheritance |

## Testing

```bash
docker exec odoo-web odoo -d test_db -i ons_discuss_threads --test-enable --stop-after-init --no-http
```
