/** @odoo-module **/

import { Component, onMounted, onWillUnmount, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";

export class CardTemplateSummary extends Component {
    static template = "wd_global_search.CardTemplateSummary";
    static props = { ...standardWidgetProps };

    setup() {
        this.http = useService("http");
        this.state = useState({
            rendered: "",
            message: "Loading card preview…",
            isError: false,
            pending: false,
            busy: false,
        });
        this.pageShowListener = () => this.loadPreview();
        this.focusListener = () => this.loadPreview();
        this.popStateListener = (event) => {
            if (event.state?.wdCardTemplateEditor) {
                this.openEditorFrame(false);
            } else {
                this.removeEditorFrame();
            }
        };
        this.messageListener = (event) => {
            if (
                event.origin === window.location.origin &&
                event.source === this.editorFrame?.contentWindow &&
                event.data?.type === "wd_global_search.close_card_template_editor"
            ) {
                window.history.back();
            }
        };
        onMounted(() => {
            window.addEventListener("pageshow", this.pageShowListener);
            window.addEventListener("focus", this.focusListener);
            window.addEventListener("popstate", this.popStateListener);
            window.addEventListener("message", this.messageListener);
            this.loadPreview();
        });
        onWillUnmount(() => {
            window.removeEventListener("pageshow", this.pageShowListener);
            window.removeEventListener("focus", this.focusListener);
            window.removeEventListener("popstate", this.popStateListener);
            window.removeEventListener("message", this.messageListener);
            this.removeEditorFrame();
        });
    }

    get resourceId() {
        return this.props.record.resId;
    }

    async loadPreview() {
        if (!this.resourceId || this.state.busy) {
            return;
        }
        this.state.busy = true;
        this.state.message = "Loading card preview…";
        this.state.isError = false;
        try {
            const descriptor = await this.http.get(
                `/wd_global_search/card_templates/descriptor?resource_id=${encodeURIComponent(this.resourceId)}`
            );
            if (descriptor.status !== "SUCCESS") {
                throw new Error("Unable to load this Resource's card template.");
            }
            const preview = await this.http.post(
                "/wd_global_search/card_templates/preview",
                {
                    resource_id: this.resourceId,
                    template: descriptor.template,
                    source: "latest_readable_record",
                    csrf_token: odoo.csrf_token,
                }
            );
            if (preview.status !== "SUCCESS") {
                throw new Error(preview.message || "Unable to render the card preview.");
            }
            this.state.rendered = preview.rendered_plain_text || "—";
            this.state.pending = Boolean(descriptor.pending);
            this.state.message = descriptor.migration_warning || "";
        } catch (error) {
            this.state.rendered = "";
            this.state.message = error.message || "Unable to load the card preview.";
            this.state.isError = true;
        } finally {
            this.state.busy = false;
        }
    }

    editTemplate() {
        if (!this.resourceId || this.editorFrame) {
            return;
        }
        this.openEditorFrame(true);
    }

    openEditorFrame(pushHistory) {
        if (this.editorFrame) {
            return;
        }
        if (pushHistory) {
            const currentState = window.history.state;
            const resourceState =
                currentState && typeof currentState === "object" ? { ...currentState } : {};
            const returnState = { ...resourceState, skipRouteChange: true };
            window.history.replaceState(returnState, "", window.location.href);
            window.history.pushState(
                {
                    ...returnState,
                    wdCardTemplateEditor: true,
                    cardTemplateResourceId: this.resourceId,
                },
                "",
                window.location.href
            );
        }
        this.editorFrame = document.createElement("iframe");
        this.editorFrame.className = "wd-template-editor-frame";
        this.editorFrame.title = "Card Template Editor";
        this.editorFrame.src =
            `/wd_global_search/card_templates?resource_id=${encodeURIComponent(this.resourceId)}`;
        document.body.append(this.editorFrame);
    }

    removeEditorFrame() {
        this.editorFrame?.remove();
        this.editorFrame = null;
    }
}

registry.category("view_widgets").add("wd_card_template_summary", {
    component: CardTemplateSummary,
});
