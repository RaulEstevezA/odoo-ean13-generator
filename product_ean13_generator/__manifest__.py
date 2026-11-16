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
        "views/res_config_settings_views.xml",
        "views/product_product_views.xml",
    ],
    "installable": True,
    "application": False,
}