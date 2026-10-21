{
    "name": "Office Engine Odoo Request Persistence",
    "version": "18.0.1.0.0",
    "category": "Productivity/Office",
    "summary": "Private Odoo request and attachment persistence for Office Engine",
    "license": "LGPL-3",
    "depends": ["base", "mail", "llm_thread"],
    "data": [
        "security/ir.model.access.csv",
        "security/office_document_request_rules.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
