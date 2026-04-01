# 01 — Direct Edit Inventory

**Date:** 2026-04-01  

## Summary

**Zero direct edits exist in Odoo core files.**

All customizations were already contained in the `discuss_thread_admin` custom addon
(originally at v19.0.5.2.0). This addon has been decomposed into 5 focused `ons_*`
addons as part of Phase 0.

## Decomposition Map

The original monolith contained 28+ source files. Each was mapped to a target addon:

### ons_discuss_ui (visual/theme/layout + config)
| Original File | New Location | Type |
|--------------|--------------|------|
| `static/src/scss/discord_theme.scss` | `ons_discuss_ui/static/src/scss/` | SCSS |
| `static/src/scss/discord_theme.dark.scss` | `ons_discuss_ui/static/src/scss/` | SCSS |
| `static/src/js/work_status_dropdown.js` | `ons_discuss_ui/static/src/js/` | JS (OWL) |
| `static/src/xml/work_status_dropdown.xml` | `ons_discuss_ui/static/src/xml/` | QWeb |
| `static/src/js/discuss_ux_patch.js` | `ons_discuss_ui/static/src/js/` | JS patch |
| `static/src/js/category_config_patch.js` | `ons_discuss_ui/static/src/js/` | JS patch |
| `static/src/js/store_service_patch.js` | `ons_discuss_ui/static/src/js/` | JS patch |
| `controllers/channel.py` (set_work_status) | `ons_discuss_ui/controllers/channel.py` | Controller |
| `controllers/im_status.py` | `ons_discuss_ui/controllers/im_status.py` | Controller |
| `models/res_config_settings.py` (5 fields) | `ons_discuss_ui/models/res_config_settings.py` | Model |
| `models/res_users.py` (work_status + store) | `ons_discuss_ui/models/res_users.py` | Model |
| `views/res_config_settings_views.xml` (partial) | `ons_discuss_ui/views/` | XML view |

### ons_discuss_threads (thread/channel behavior)
| Original File | New Location | Type |
|--------------|--------------|------|
| `static/src/js/thread_actions_patch.js` | `ons_discuss_threads/static/src/js/` | JS patch |
| `static/src/js/delete_thread_dialog_patch.js` | `ons_discuss_threads/static/src/js/` | JS patch |
| `static/src/js/message_actions_patch.js` | `ons_discuss_threads/static/src/js/` | JS patch |
| `static/src/js/channel_actions_patch.js` | `ons_discuss_threads/static/src/js/` | JS patch |
| `static/src/js/leave_channel_patch.js` | `ons_discuss_threads/static/src/js/` | JS patch |
| `static/src/js/sidebar_reorder_patch.js` | `ons_discuss_threads/static/src/js/` | JS patch |
| `static/src/js/store_service_patch.js` (Thread.sequence) | `ons_discuss_threads/static/src/js/` | JS patch |
| `static/src/xml/sidebar_reorder.xml` | `ons_discuss_threads/static/src/xml/` | QWeb |
| `controllers/channel.py` (delete/kick/reorder/intake) | `ons_discuss_threads/controllers/channel.py` | Controller |
| `models/discuss_channel.py` (sequence + cleanup) | `ons_discuss_threads/models/discuss_channel.py` | Model |
| `models/discuss_intake.py` | `ons_discuss_threads/models/discuss_intake.py` | Model |
| `views/admin_views.xml` | `ons_discuss_threads/views/` | XML view |
| `security/ir.model.access.csv` | `ons_discuss_threads/security/` | ACL |

### ons_discuss_voice (voice/RTC behavior)
| Original File | New Location | Type |
|--------------|--------------|------|
| `static/src/js/voice_channel_patch.js` | `ons_discuss_voice/static/src/js/` | JS patch |
| `static/src/js/store_service_patch.js` (Thread.is_voice_channel) | `ons_discuss_voice/static/src/js/` | JS patch |
| `static/src/xml/voice_channel_sidebar.xml` | `ons_discuss_voice/static/src/xml/` | QWeb |
| `controllers/channel.py` (set_voice_channel) | `ons_discuss_voice/controllers/channel.py` | Controller |
| `models/discuss_channel.py` (is_voice_channel + message_post) | `ons_discuss_voice/models/discuss_channel.py` | Model |
| `models/discuss_channel_rtc_session.py` | `ons_discuss_voice/models/` | Model |
| `views/admin_views.xml` | `ons_discuss_voice/views/` | XML view |

### ons_gif_provider (GIF/media integration)
| Original File | New Location | Type |
|--------------|--------------|------|
| `controllers/gif.py` | `ons_gif_provider/controllers/gif.py` | Controller |
| `static/src/js/gif_composer_patch.js` | `ons_gif_provider/static/src/js/` | JS patch |
| `models/res_config_settings.py` (giphy_api_key) | `ons_gif_provider/models/res_config_settings.py` | Model |
| `models/res_users.py` (gif feature flag) | `ons_gif_provider/models/res_users.py` | Model |
| `views/res_config_settings_views.xml` (partial) | `ons_gif_provider/views/` | XML view |

### ons_webrtc (server config/environment)
| Original File | New Location | Type |
|--------------|--------------|------|
| (new) `controllers/health.py` | `ons_webrtc/controllers/health.py` | Controller |

## Direct Core Debt Remaining

**None.** All customizations now live in the `ons_*` addon layer.
