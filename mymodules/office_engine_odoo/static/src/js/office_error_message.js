/** @odoo-module **/

import { Message } from "@mail/core/common/message";
import { Message as MessageModel } from "@mail/core/common/message_model";
import { Record } from "@mail/core/common/record";
import { patch } from "@web/core/utils/patch";

patch(MessageModel.prototype, {
    setup() {
        super.setup(...arguments);
        this.is_error = Record.attr(false);
    },
});

patch(Message.prototype, {
    get className() {
        const className = super.className || "";
        const message = this.props.message;
        if (message?.model === "llm.thread" && message.is_error) {
            return `${className} o-office-chat-error`;
        }
        return className;
    },
});
