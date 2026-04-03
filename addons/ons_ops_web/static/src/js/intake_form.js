/** @odoo-module **/
import { FormController } from "@web/views/form/form_controller";
import { ListController } from "@web/views/list/list_controller";
import { KanbanController } from "@web/views/kanban/kanban_controller";
import { patch } from "@web/core/utils/patch";
import { onMounted, onPatched } from "@odoo/owl";

/**
 * Add model-specific CSS class to view root elements so SCSS can target
 * them. Also enhance ons.interaction forms with session path icons and
 * numbered section badges matching the legacy dashboard.
 */

function addModelClass(el, resModel) {
    if (!el || !resModel) return;
    const cls = "ons_model_" + resModel.replace(/\./g, "_");
    if (!el.classList.contains(cls)) {
        el.classList.add(cls);
    }
}

// ── Form Controller patch ──
patch(FormController.prototype, {
    setup() {
        super.setup(...arguments);
        onMounted(() => this._onsEnhanceForm());
        onPatched(() => this._onsEnhanceForm());
    },

    _onsEnhanceForm() {
        const el = this.rootRef?.el;
        if (!el) return;

        const model = this.props?.resModel;
        addModelClass(el, model);

        if (model === "ons.interaction") {
            this._onsAddSessionPathIcons(el);
            this._onsAddSectionNumbers(el);
        }
    },

    _onsAddSessionPathIcons(el) {
        const radioItems = el.querySelectorAll(
            '.o_field_widget[name="session_path"] .o_radio_item'
        );

        const icons = [
            { path: 'M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z', color: '#CA8A04' },
            { path: 'M20 3H4a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V5a2 2 0 0 0-2-2z M8 21h8 M12 17v4', color: '#16A34A' },
            { path: 'M8 2v4 M16 2v4 M3 10h18 M5 4h14a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2z', color: '#2563EB' },
            { path: 'M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0z M12 7a3 3 0 1 0 0 6a3 3 0 0 0 0-6z', color: '#EA580C' },
        ];

        radioItems.forEach((item, i) => {
            if (i >= icons.length || item.querySelector('.ons-session-icon')) return;

            const { path, color } = icons[i];
            const indicator = document.createElement('span');
            indicator.className = 'ons-session-icon';
            indicator.style.cssText = `
                display:inline-flex; align-items:center; justify-content:center;
                width:32px; height:32px; border-radius:8px;
                background-color:${color}12; flex-shrink:0; order:-1;
            `;
            indicator.innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="${color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="${path}"/></svg>`;

            item.insertBefore(indicator, item.firstChild);
        });
    },

    _onsAddSectionNumbers(el) {
        const sectionColors = [
            '#4B7BEB', // Call Story
            '#16A34A', // Customer
            '#14B8A6', // Call Details
            '#7C3AED', // Session Intent
            '#EA580C', // Onsite Address
            '#475569', // Role Assignment
            '#CA8A04', // Driver Classification
        ];

        // Odoo 19 renders group string= as div.o_horizontal_separator
        const separators = el.querySelectorAll('.o_horizontal_separator');
        separators.forEach((sep, i) => {
            if (i >= sectionColors.length || sep.querySelector('.ons-section-num')) return;

            const color = sectionColors[i];
            const badge = document.createElement('span');
            badge.className = 'ons-section-num';
            badge.style.cssText = `
                display:inline-flex; align-items:center; justify-content:center;
                width:22px; height:22px; border-radius:50%;
                background-color:${color}; color:white;
                font-size:11px; font-weight:700; margin-right:8px; flex-shrink:0;
                vertical-align:middle;
            `;
            badge.textContent = String(i + 1);
            sep.insertBefore(badge, sep.firstChild);
        });
    },
});

// ── List Controller patch ──
patch(ListController.prototype, {
    setup() {
        super.setup(...arguments);
        onMounted(() => {
            addModelClass(this.rootRef?.el, this.props?.resModel);
        });
        onPatched(() => {
            addModelClass(this.rootRef?.el, this.props?.resModel);
        });
    },
});

// ── Kanban Controller patch ──
patch(KanbanController.prototype, {
    setup() {
        super.setup(...arguments);
        onMounted(() => {
            addModelClass(this.rootRef?.el, this.props?.resModel);
        });
        onPatched(() => {
            addModelClass(this.rootRef?.el, this.props?.resModel);
        });
    },
});
