{
    "name": "Generador EAN-13 para productos",
    "version": "18.0.1.0.0",
    "summary": "Generación de códigos EAN-13 para variantes de producto",
    "category": "Inventory/Inventory",
    "author": "Raúl Estévez",
    "license": "AGPL-3",
    "depends": [
        "base_setup",
        "product",
    ],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "views/res_config_settings_views.xml",
        "views/product_product_views.xml",
        "views/product_template_views.xml",
        "views/ean13_generate_wizard_views.xml",
    ],
    "pre_init_hook": "pre_init_hook",
    "installable": True,
    "application": False,
}