# 02 — Upgrade Risk Matrix

**Date:** 2026-04-01  
**Current Version:** Odoo 19.0-20260324  
**Target Upgrade:** Odoo 20.0+  

## Risk Categories

- **HIGH** — Will almost certainly break on a major Odoo version upgrade.
  Active maintenance required.
- **MEDIUM** — May break if Odoo refactors the affected area.
  Monitor upstream changelogs.
- **LOW** — Unlikely to break. Uses stable APIs or standalone models.

## Risk Register

### HIGH Risk Items

| # | Addon | Component | What Could Break | Mitigation |
|---|-------|-----------|-----------------|------------|
| H1 | ons_discuss_voice | `discuss.channel.rtc.session.create()` override | Stock RTC session creation logic changes, different context keys, different call history model | Pin to tested Odoo commit; add integration test; review RTC changes in each Odoo release |
| H2 | ons_discuss_voice | `discuss.channel.message_post()` override | Stock message_post signature or call notification format changes | Test against new Odoo version before upgrade; look for `data-oe-type="call"` format changes |
| H3 | ons_discuss_ui | SCSS theme (300+ lines per file) | Odoo refactors Discuss CSS class names (`.o_Discuss*`, `.o-mail-*`) | Maintain a selector compatibility test; compare upstream SCSS diff on each upgrade |

### MEDIUM Risk Items

| # | Addon | Component | What Could Break | Mitigation |
|---|-------|-----------|-----------------|------------|
| M1 | ons_discuss_threads | 7 JS patches (Thread, Store, Composer, etc.) | Owl component names, props, or registry structure changes | Each patch uses `@web/core/utils/patch` — review upstream for removed/renamed components |
| M2 | ons_discuss_voice | `voice_channel_patch.js` patches `DiscussClientAction` | Odoo moves Discuss to a different client action class | Monitor `@mail/core/web/discuss_client_action` import path |
| M3 | ons_gif_provider | `DiscussGifController` inheritance | Odoo removes/renames stock GIF endpoints or changes Tenor→something else | If Odoo adopts GIPHY natively, this addon becomes unnecessary (remove) |
| M4 | ons_gif_provider | `gif_composer_patch.js` patches `Composer.sendGifMessage` | Odoo changes how GIFs are sent in Composer | Check if `sendGifMessage` still exists on Composer prototype |
| M5 | ons_discuss_ui | `WorkStatusDropdown` replaces stock IM status in `user_menuitems` registry | Odoo changes the user menu registry structure | Review `@web/core/user_menuitems_registry` on each upgrade |
| M6 | ons_discuss_threads | `discuss.channel._action_unfollow` override | Stock unfollow behavior or signature changes | Compare `_action_unfollow` diff on each upgrade |
| M7 | ons_discuss_ui | Settings view XPath after `activities_setting` | Stock settings view restructured | Verify XPath target exists before upgrade |

### LOW Risk Items

| # | Addon | Component | What Could Break | Mitigation |
|---|-------|-----------|-----------------|------------|
| L1 | ons_discuss_threads | `discuss.intake` model | Nearly impossible — it's a new model we own | None needed |
| L2 | ons_discuss_threads | `sequence` field on `discuss.channel` | Odoo adds their own `sequence` field (unlikely) | Check for field name collision |
| L3 | ons_discuss_voice | `is_voice_channel` field on `discuss.channel` | Odoo adds native voice channels (desirable!) | If Odoo adds this natively, remove our field and use theirs |
| L4 | ons_webrtc | Health check controller | Standalone endpoint, no overrides | None needed |
| L5 | ons_gif_provider | `discuss.giphy_api_key` config parameter | No collision expected | None needed |
| L6 | All | `discuss_thread_admin.*` config parameter keys | Legacy prefix from original addon | Document; migrate keys if/when convenient |

## Upgrade Procedure (for each major Odoo version)

1. **Pre-upgrade**: Run all Python tests against a **copy** of the production database on the new Odoo version
2. **Asset check**: Verify all JS imports still resolve (`@mail/core/*`, `@web/core/*`)
3. **SCSS check**: Compare upstream Discuss CSS class changes
4. **XPath check**: Verify all XML inheritance targets still exist
5. **Controller check**: Verify overridden stock controller routes still exist
6. **Functional test**: Open Discuss → verify theme, work status, GIF picker, voice channels, reorder, intake
7. **RTC test**: Join a voice channel, verify auto-join works and notifications are suppressed
