/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { Message } from "@mail/core/common/message";
import { patch } from "@web/core/utils/patch";
import { rpc } from "@web/core/network/rpc";

export class OfficeMappingCard extends Component {
    static template = "office_engine_m2.OfficeMappingCard";
    static props = { message: { type: Object } };

    setup() {
        const payload = this.props.message.body_json?.office_mapping_card || {};
        this.state = useState({
            sessionId: payload.session_id,
            revision: payload.revision,
            status: "Loading mapping options…",
            busy: false,
            targets: [],
            fields: [],
        });
        onWillStart(() => this.loadContext());
    }

    async loadContext() {
        try {
            const result = await rpc("/office_engine_m2/mapping/context", {
                session_id: this.state.sessionId,
                expected_revision: this.state.revision,
            });
            this.state.revision = result.revision;
            this.state.targets = result.targets.map((target) => ({ ...target }));
            this.state.fields = result.fields;
            this.state.status = result.stale
                ? "Mapping refreshed to the latest revision."
                : "Ready to edit.";
        } catch {
            this.state.status = "Mapping is unavailable. Refresh or contact an administrator.";
        }
    }

    onFieldChange(ev) {
        const index = Number(ev.currentTarget.dataset.targetIndex);
        this.state.targets[index].source_field = ev.currentTarget.value;
    }

    get edits() {
        return this.state.targets
            .filter((target) => target.source_field)
            .map((target) => {
                const field = this.state.fields.find((item) => item.field_id === target.source_field);
                return {
                    element_id: target.element_id,
                    source_field: target.source_field,
                    value_type: field?.value_type || "",
                };
            });
    }

    async save() {
        await this.perform("/office_engine_m2/mapping/update", { edits: this.edits }, "Mapping saved.");
    }

    async confirm() {
        await this.perform("/office_engine_m2/mapping/confirm", {}, "Mapping confirmed.");
    }

    async cancel() {
        await this.perform("/office_engine_m2/mapping/cancel", {}, "Mapping cancelled.");
    }

    async perform(route, extra, successText) {
        if (this.state.busy) {
            return;
        }
        this.state.busy = true;
        try {
            const result = await rpc(route, {
                session_id: this.state.sessionId,
                expected_revision: this.state.revision,
                ...extra,
            });
            this.state.revision = result.revision;
            this.state.status = result.state === "needs_clarification"
                ? "Some required mappings need clarification."
                : successText;
        } catch {
            this.state.status = "The request was rejected or the session changed. Reload the card and retry.";
        } finally {
            this.state.busy = false;
        }
    }
}

patch(Message, {
    components: { ...Message.components, OfficeMappingCard },
});

patch(Message.prototype, {
    get isOfficeMappingCard() {
        const message = this.props.message;
        return message?.model === "llm.thread"
            && message?.llm_role === "assistant"
            && message?.body_json?.office_mapping_card?.type === "office_mapping_card_v1"
            && Number.isInteger(message?.body_json?.office_mapping_card?.session_id);
    },
});
