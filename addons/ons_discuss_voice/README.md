# ons_discuss_voice

**Version:** 19.0.1.0.0  
**License:** LGPL-3  
**Depends:** mail, ons_discuss_threads  

## Purpose

Voice channel behavior for Odoo Discuss:
- `is_voice_channel` flag on `discuss.channel`
- Auto-join RTC when entering a voice channel (JS)
- Auto-leave RTC when navigating away (JS)
- Suppress "started a call" notifications for always-on voice channels
- Clean up orphaned `discuss.call.history` records from suppressed notifications
- Speaker icon overlay in sidebar for voice channels
- Admin toggle to mark channels as voice channels

## Models

- **discuss.channel** (inherited) — `is_voice_channel` field, `message_post` override
- **discuss.channel.rtc.session** (inherited) — `create` override for notification suppression

## Routes

| Route | Auth | Purpose |
|-------|------|---------|
| `/discuss/channel/admin/set_voice_channel` | admin | Toggle voice channel flag |

## Upgrade Notes

| Risk | Component | Detail |
|------|-----------|--------|
| HIGH | `discuss.channel.rtc.session.create` | Override — fragile if stock RTC session creation changes |
| HIGH | `discuss.channel.message_post` | Override — fragile if stock message_post signature/behavior changes |
| MEDIUM | JS `voice_channel_patch.js` | Patches `DiscussClientAction` for auto-join/leave behavior |
| LOW | `is_voice_channel` field | Simple Boolean, no collision risk |
| LOW | Admin view | Inherits `ons_discuss_threads` tree view |

## Testing

```bash
docker exec odoo-web odoo -d test_db -i ons_discuss_voice --test-enable --stop-after-init --no-http
```
