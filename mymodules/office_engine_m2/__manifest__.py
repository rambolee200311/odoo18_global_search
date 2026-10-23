{
    "name": "Office Engine M2 Usage Metering",
    "version": "18.0.1.0.0",
    "category": "Productivity/Office",
    "summary": "Restricted metadata-only LLM usage metering for Office Engine",
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
        "security/ir.model.access.csv",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
