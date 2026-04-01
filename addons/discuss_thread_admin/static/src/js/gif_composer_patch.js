/** @odoo-module **/
/**
 * Patch the Composer so that selecting a GIF renders it as an inline
 * <img> instead of a plain hyperlink.  The stock Odoo code posts
 * `gif.url` wrapped in an <a> tag, which for GIPHY is either a page
 * URL or (after our backend fix) a direct media URL — but either way
 * an <a> tag won't render the image inline.
 */
import { Composer } from "@mail/core/common/composer";
import { patch } from "@web/core/utils/patch";
import { markup } from "@odoo/owl";

patch(Composer.prototype, {
    async sendGifMessage(gif) {
        // Prefer the direct media URL; fall back to tinygif thumbnail
        const src = gif.url || gif.media_formats?.tinygif?.url;
        if (!src) {
            return;
        }
        const alt = gif.content_description || gif.title || "GIF";
        await this._sendMessage(
            markup`<img src="${src}" alt="${alt}" style="max-width:400px;max-height:300px;" />`,
            {
                parentId: this.props.composer.replyToMessage?.id,
            }
        );
    },
});
