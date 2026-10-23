/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { Message } from "@mail/core/common/message";
import { patch } from "@web/core/utils/patch";
import { rpc } from "@web/core/network/rpc";

export class TVM2MappingCard extends Component {
  static template = "tv_office_m2_owl.MappingCard";

  setup() {
    this.state = useState({ fieldKey: "partner_id.name", status: "" });
  }

  onChange(ev) {
    this.state.fieldKey = ev.target.value;
  }

  async submit() {
    const result = await rpc("/tv_office_m2_owl/validate_selection", {
      field_key: this.state.fieldKey,
    });
    this.state.status = result.accepted
      ? `Server accepted ${result.field_key}`
      : "Server rejected the selection";
  }
}

patch(Message, {
  components: { ...Message.components, TVM2MappingCard },
});

patch(Message.prototype, {
  get isTVM2MappingCard() {
    const message = this.props.message;
    return (
      message?.model === "llm.thread" &&
      typeof message.body === "string" &&
      message.body.includes("TV-M2-CARD")
    );
  },
});
