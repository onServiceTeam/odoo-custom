# ons_gif_provider

**Version:** 19.0.1.0.0  
**License:** LGPL-3  
**Depends:** mail  

## Purpose

Replaces the discontinued Google Tenor GIF API (shut down January 2026) with
GIPHY as the GIF provider for Odoo Discuss:
- Full GIPHY controller overriding stock `/discuss/gif/*` endpoints
- Search, trending categories, and favorites
- GIPHY API key management in Settings
- Hides stock Tenor API key field
- Inline `<img>` rendering for GIFs (instead of link-only)
- XSS-safe URL validation and HTML attribute escaping

## Configuration

Settings > Discuss > **GIPHY API Key**: Enter a GIPHY API key from
[developers.giphy.com](https://developers.giphy.com).

## Routes

Overrides stock `DiscussGifController`:
| Route | Purpose |
|-------|---------|
| `/discuss/gif/search` | Search GIPHY for GIFs |
| `/discuss/gif/categories` | Show trending GIFs as category tiles |
| `/discuss/gif/favorites` | Fetch user's favorited GIFs from GIPHY |

## Upgrade Notes

| Risk | Component | Detail |
|------|-----------|--------|
| MEDIUM | `DiscussGifController` inheritance | Overrides all 3 stock GIF endpoints — if Odoo changes signatures or removes them, this breaks |
| MEDIUM | `gif_composer_patch.js` | Patches `Composer.prototype.sendGifMessage` — fragile if Odoo changes Composer |
| LOW | XPath `tenor_api_key` replace | Hides stock Tenor field — verified present in Odoo 19.0-20260324 |
| LOW | `discuss.giphy_api_key` config parameter | Custom key, no collision |

## Testing

```bash
docker exec odoo-web odoo -d test_db -i ons_gif_provider --test-enable --stop-after-init --no-http
```
