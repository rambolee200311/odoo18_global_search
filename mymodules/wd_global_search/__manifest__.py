{
    "name": "WD Global Search",
    "version": "18.0.1.0.0",
    "category": "Tools",
    "summary": "Read-only global search preview workspace",
    "depends": ["base", "web", "sale", "stock"],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "views/configuration_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "wd_global_search/static/src/css/preview.css",
            "wd_global_search/static/src/js/preview.js",
        ],
    },
    "installable": True,
    "application": True,
    "license": "LGPL-3",
}
