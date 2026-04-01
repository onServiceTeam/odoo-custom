# -*- coding: utf-8 -*-
"""
GIPHY GIF integration for Odoo Discuss.

Replaces the discontinued Google Tenor API (shut down January 2026) with
GIPHY as the GIF provider.  Overrides the stock /discuss/gif/* endpoints
so the existing JS GIF picker works without modification.

The GIPHY API key is stored as ``discuss.giphy_api_key`` in
ir.config_parameter and managed via Settings > Discuss > GIPHY API Key.
"""
import logging
import requests
import urllib3
from werkzeug.exceptions import BadRequest

from odoo.http import request, route
from odoo.addons.mail.controllers.discuss.gif import DiscussGifController

_logger = logging.getLogger(__name__)

GIPHY_BASE_URL = "https://api.giphy.com/v1/gifs"
GIPHY_GIF_LIMIT = 8
GIPHY_RATING = "pg-13"


def _giphy_to_picker_format(giphy_gif):
    """Convert a GIPHY response object to the format the JS GIF picker expects.

    The stock Odoo picker was built for Tenor's data shape.  We map GIPHY
    fields into the same structure so the frontend works unchanged.
    """
    small = giphy_gif.get("images", {}).get("fixed_height_small", {})
    original = giphy_gif.get("images", {}).get("original", {})
    # Direct media URL for embedding in chat — downsized_medium gives
    # good quality without excessive file size; fall back to original.
    downsized = giphy_gif.get("images", {}).get("downsized_medium", {})
    media_url = downsized.get("url") or original.get("url", "")
    return {
        "id": giphy_gif.get("id", ""),
        "title": giphy_gif.get("title", ""),
        "created": 0,
        "content_description": giphy_gif.get("title", ""),
        "itemurl": giphy_gif.get("url", ""),
        # url: the direct GIF media link used when posting into chat
        "url": media_url,
        "tags": [],
        "flags": [],
        "hasaudio": False,
        "media_formats": {
            "tinygif": {
                "url": small.get("url", original.get("url", "")),
                "dims": [
                    int(small.get("width", 100)),
                    int(small.get("height", 100)),
                ],
                "size": int(small.get("size", 0)),
                "duration": 0,
                "preview": "",
            }
        },
    }


class DiscussGifControllerInherit(DiscussGifController):
    """Override stock GIF endpoints to use GIPHY instead of Tenor.

    Google discontinued the Tenor API in January 2026.  This controller
    replaces all GIF search/category/favorite endpoints with GIPHY
    equivalents while returning data in the same shape the JS picker
    expects.
    """

    def _get_giphy_api_key(self):
        """Return the configured GIPHY API key, or None."""
        return (
            request.env["ir.config_parameter"]
            .sudo()
            .get_param("discuss.giphy_api_key")
        )

    def _request_giphy(self, endpoint, params):
        """Make a request to the GIPHY API and return parsed JSON."""
        try:
            url = f"{GIPHY_BASE_URL}/{endpoint}"
            response = requests.get(url, params=params, timeout=5)
            response.raise_for_status()
            return response.json()
        except (
            requests.exceptions.RequestException,
            urllib3.exceptions.MaxRetryError,
        ) as e:
            _logger.error("GIPHY API request failed: %s", e)
            return None

    @route("/discuss/gif/search", type="jsonrpc", auth="user")
    def search(self, search_term, locale="en", country="US", position=None, readonly=True):
        key = self._get_giphy_api_key()
        if not key:
            raise BadRequest("GIPHY API key not configured")

        offset = int(position) if position else 0
        data = self._request_giphy("search", {
            "api_key": key,
            "q": search_term,
            "limit": GIPHY_GIF_LIMIT,
            "offset": offset,
            "rating": GIPHY_RATING,
            "lang": locale[:2] if locale else "en",
        })
        if not data:
            raise BadRequest()
        results = [_giphy_to_picker_format(g) for g in data.get("data", [])]
        pagination = data.get("pagination", {})
        next_offset = pagination.get("offset", 0) + pagination.get("count", 0)
        return {
            "next": str(next_offset),
            "results": results,
        }

    @route("/discuss/gif/categories", type="jsonrpc", auth="user", readonly=True)
    def categories(self, locale="en", country="US"):
        key = self._get_giphy_api_key()
        if not key:
            raise BadRequest("GIPHY API key not configured")

        # GIPHY doesn't have a categories endpoint like Tenor did.
        # Show trending GIFs as clickable category tiles instead.
        data = self._request_giphy("trending", {
            "api_key": key,
            "limit": GIPHY_GIF_LIMIT,
            "rating": GIPHY_RATING,
        })
        if not data:
            raise BadRequest()
        tags = []
        for gif in data.get("data", []):
            title = gif.get("title", "").split(" GIF")[0].strip() or "Trending"
            still = gif.get("images", {}).get("fixed_height_small_still", {})
            tags.append({
                "searchterm": title,
                "path": f"#q={title}",
                "image": still.get("url", ""),
                "name": title,
            })
        return {"tags": tags}

    @route("/discuss/gif/favorites", type="jsonrpc", auth="user", readonly=True)
    def get_favorites(self, offset=0):
        key = self._get_giphy_api_key()
        if not key:
            return ([],)

        # Favorites use the stock discuss.gif.favorite model which stores
        # the GIF provider ID in the ``tenor_gif_id`` field (legacy name
        # from when Odoo used Tenor — the field stores GIPHY IDs now).
        favorites = request.env["discuss.gif.favorite"].search(
            [("create_uid", "=", request.env.user.id)], limit=20, offset=offset
        )
        if not favorites:
            return ([],)
        ids = ",".join(favorites.mapped("tenor_gif_id"))
        try:
            response = requests.get(
                GIPHY_BASE_URL,
                params={"api_key": key, "ids": ids},
                timeout=5,
            )
            response.raise_for_status()
            data = response.json()
        except (
            requests.exceptions.RequestException,
            urllib3.exceptions.MaxRetryError,
        ):
            return ([],)
        if not data:
            return ([],)
        results = [_giphy_to_picker_format(g) for g in data.get("data", [])]
        return (results,)
