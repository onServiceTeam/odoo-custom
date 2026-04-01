# discuss_thread_admin

**Version:** 19.0.6.0.0  
**License:** LGPL-3  
**Depends:** ons_discuss_ui, ons_gif_provider, ons_discuss_threads, ons_discuss_voice, ons_webrtc  

## Purpose

Meta-package that installs all onService Discuss customization addons. This was
the original monolith addon; it has been decomposed into 5 focused `ons_*` addons
as of v6.0.0.

**This module contains no code.** It exists solely to:
1. Provide a single install point for all Discuss customizations
2. Maintain backward compatibility for users who already had it installed

## Migration History

| Version | Change |
|---------|--------|
| 19.0.5.2.0 | Original monolith with all Discuss features |
| 19.0.6.0.0 | Decomposed into ons_discuss_ui, ons_gif_provider, ons_discuss_threads, ons_discuss_voice, ons_webrtc |
