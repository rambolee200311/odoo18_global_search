{
    "name": "WD Global Search",
    "version": "18.0.1.1.0",
    "category": "Tools",
    "summary": "Read-only global search workspace",
    "depends": ["base", "web", "sale", "purchase", "stock"],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "views/configuration_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "wd_global_search/static/src/xml/template_designer.xml",
            "wd_global_search/static/src/js/template_designer_field.js",
            "wd_global_search/static/src/css/template_designer.css",
        ],
    },
    "installable": True,
    "application": True,
    "license": "LGPL-3",
}
