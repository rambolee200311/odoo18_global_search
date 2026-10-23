{
    "name": "Office Engine M2 Orchestration",
    "version": "18.0.2.0.0",
    "category": "Productivity/Office",
    "summary": "User-scoped Office mapping sessions and restricted usage metering",
    "license": "LGPL-3",
    "depends": [
        "base",
        "office_engine_odoo",
        "llm_assistant",
        "llm_tool",
        "llm_openai",
    ],
    "data": [
        "security/office_engine_m2_groups.xml",
        "security/office_mapping_session_rules.xml",
        "security/ir.model.access.csv",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
