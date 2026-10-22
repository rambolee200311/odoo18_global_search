{
    "name": "Office Engine Odoo Request Persistence",
    "version": "18.0.1.4.0",
    "category": "Productivity/Office",
    "summary": "Private Odoo request and attachment persistence for Office Engine",
    "license": "LGPL-3",
    "depends": ["base", "mail", "web", "llm_thread"],
    "data": [
        "security/ir.model.access.csv",
        "security/office_document_request_rules.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "office_engine_odoo/static/src/js/office_error_message.js",
            "office_engine_odoo/static/src/scss/office_error_message.scss",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
}
