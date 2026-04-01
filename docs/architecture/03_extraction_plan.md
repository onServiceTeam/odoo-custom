# 03 — Extraction Plan

**Date:** 2026-04-01  
**Status:** COMPLETE  

## Context

The original `discuss_thread_admin` addon (v19.0.5.2.0) was a monolith containing
28+ source files covering 5 distinct concern areas. This document records the
extraction plan and its execution.

## Extraction Strategy

1. **Read all source files** from the monolith to understand boundaries
2. **Classify each file** by concern area (UI, threads, voice, GIF, WebRTC)
3. **Create 5 target addon scaffolds** with proper manifests and dependencies
4. **Extract files** into their target addons, adjusting imports and references
5. **Convert the monolith** into a dependency-only meta-package
6. **Deploy and verify** all features still work
7. **QA audit** for dead code, route conflicts, XSS, naming issues
8. **Fix all issues found** and commit

## Dependency Design

```
mail (stock)
 ├── ons_discuss_ui
 │    └── ons_discuss_threads
 │         └── ons_discuss_voice
 ├── ons_gif_provider
 ├── ons_webrtc
 └── discuss_thread_admin (meta → installs all above)
```

**Rationale:**
- `ons_discuss_ui` has no custom addon deps (only `mail`) — it provides foundational UI + config
- `ons_discuss_threads` depends on `ons_discuss_ui` because it uses config settings defined there
- `ons_discuss_voice` depends on `ons_discuss_threads` because its admin view inherits the threads tree view
- `ons_gif_provider` and `ons_webrtc` are independent — they only need `mail`

## Execution Log

| Step | Commit | Result |
|------|--------|--------|
| Baseline snapshot | `04f7ab4` | Git init, DB backup |
| Extraction + deployment | `2cd6815` | All 6 modules installed, zero errors |
| QA fixes (dead code, XSS, field rename) | `2997db9` | 11 issues fixed, clean deployment |

## Post-Extraction Verification

- ✅ All 6 modules show `installed` in database
- ✅ Zero runtime errors in logs
- ✅ Zero duplicate routes across addons
- ✅ Zero orphaned ir_model_data records
- ✅ All JS template names match XML counterparts
- ✅ All static assets registered in manifests
- ✅ Config parameters preserved (`admin_only_delete`, `auto_cleanup_empty_groups`, GIPHY key)
- ✅ No Enterprise module name collisions
