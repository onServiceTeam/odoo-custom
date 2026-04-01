/** @odoo-module **/

/**
 * Discord-style voice channel behavior:
 *
 * - Navigating to a voice channel auto-joins the voice call (mic active).
 * - Navigating away auto-leaves the call.
 * - Works in both desktop (sidebar) and compact/mobile views.
 *
 * Implementation: patches DiscussClientAction.restoreDiscussThread() which
 * fires every time the URL/props change (onWillStart + onWillUpdateProps).
 * Also patches setup() to register a reactive effect on store.discuss that
 * catches sidebar-click navigation (openChannel → setAsDiscussThread).
 *
 * `this.rtc` is set by the stock call patch (`useService("discuss.rtc")`)
 * and is the RTC Record singleton with `.channel`, `.toggleCall()`,
 * `.leaveCall()`, `.joinCall()`.
 */
import { DiscussClientAction } from "@mail/core/public_web/discuss_client_action";
import { patch } from "@web/core/utils/patch";
import { effect } from "@web/core/utils/reactive";

patch(DiscussClientAction.prototype, {
    setup() {
        super.setup(...arguments);

        /** Track which voice channel we last auto-joined */
        this._voiceAutoJoinedThread = null;
        this._voiceJoinInProgress = false;

        // Reactive effect: fires whenever store.discuss changes (including .thread).
        // The `discuss` reactive proxy is passed as the first arg to the callback.
        effect(
            (discuss) => {
                const thread = discuss.thread;
                this._handleVoiceChannelNavigation(thread);
            },
            [this.store.discuss]
        );
    },

    /**
     * Handle auto-join / auto-leave for voice channels.
     * Called reactively whenever the active discuss thread changes.
     */
    async _handleVoiceChannelNavigation(thread) {
        if (!this.rtc || this._voiceJoinInProgress) return;

        const prev = this._voiceAutoJoinedThread;

        // Same thread as before — nothing to do
        if (prev && thread && prev.eq(thread)) return;

        // 1) Auto-leave: if we were in a voice channel and moved elsewhere
        if (prev && (!thread || !thread.eq(prev))) {
            this._voiceAutoJoinedThread = null;
            if (this.rtc.channel?.eq(prev)) {
                try {
                    await this.rtc.leaveCall();
                } catch (e) {
                    console.warn("[VoiceChannel] auto-leave failed:", e);
                }
            }
        }

        // 2) Auto-join: if we entered a voice channel
        if (thread?.is_voice_channel && thread?.allowCalls) {
            const alreadyInCall = this.rtc.channel?.eq(thread);
            if (!alreadyInCall) {
                this._voiceJoinInProgress = true;
                this._voiceAutoJoinedThread = thread;
                try {
                    await this.rtc.toggleCall(thread, { audio: true });
                } catch (e) {
                    console.warn("[VoiceChannel] auto-join failed:", e);
                    this._voiceAutoJoinedThread = null;
                } finally {
                    this._voiceJoinInProgress = false;
                }
            } else {
                // Already in this call (e.g. page reload)
                this._voiceAutoJoinedThread = thread;
            }
        }
    },
});
