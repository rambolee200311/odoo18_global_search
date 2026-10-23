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
            sessionState: null,
            status: "正在读取映射选项……",
            busy: false,
            mappingRows: [],
            mappingGroups: [],
            fields: [],
            clarifications: [],
            downloadUrl: "",
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
            this.state.sessionState = result.state;
            const rows = result.mapping_rows || result.targets || [];
            this.state.mappingRows = rows.map((row) => ({ ...row }));
            this.state.mappingGroups = result.mapping_groups || [];
            this.state.fields = result.fields;
            this.state.clarifications = result.clarifications || [];
            if (result.state === "completed" && result.download_url) {
                this.state.downloadUrl = result.download_url;
                this.state.status = "文档已生成并通过校验。";
            } else if (result.state === "completed") {
                this.state.status = "文档生成已完成，但当前无法获取输出文件。";
            } else if (result.stale) {
                this.state.status = "映射已刷新到最新版本。";
            } else if (result.state === "failed") {
                this.state.status = "文档生成失败，没有可下载的输出文件。";
            } else if (result.state === "cancelled") {
                this.state.status = "映射已取消。";
            } else {
                this.state.status = "可以编辑映射。";
            }
        } catch {
            this.state.status = "映射暂不可用，请刷新或联系管理员。";
        }
    }

    get edits() {
        return this.state.mappingRows
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

    get hasMissingRequired() {
        return this.state.mappingRows.some((row) => row.required && !row.source_field);
    }

    async save() {
            await this.perform("/office_engine_m2/mapping/update", { edits: this.edits }, "映射已保存。");
    }

    async confirm() {
        await this.perform("/office_engine_m2/mapping/confirm", {}, "映射已确认。");
    }

    async cancel() {
        await this.perform("/office_engine_m2/mapping/cancel", {}, "映射已取消。");
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
            this.state.sessionState = result.state;
            if (result.state === "completed" && result.download_url) {
                this.state.downloadUrl = result.download_url;
                this.state.status = "文档已生成并通过校验。";
            } else if (result.state === "needs_clarification") {
                this.state.status = "部分必填映射需要补充或澄清。";
            } else if (result.state === "failed") {
                this.state.status = "文档生成失败，没有可下载的输出文件。";
            } else {
                this.state.status = successText;
            }
        } catch {
            this.state.status = "请求被拒绝或会话版本已变化，请刷新卡片后重试。";
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
