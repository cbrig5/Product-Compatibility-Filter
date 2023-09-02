{
    "name": "Product Compatibility Filter",

    "summary": "This module will add a filter in e-commerce that will get what parts are compatible with certain products",

    "version": "1.0",
    
    "category": "Custom Development/",
    
    "license": "OPL-1",
    
    "depends": ['stock', 'website_sale', 'product'],
    
    "data": [
        "security/ir.model.access.csv",
        "views/product_template_views.xml",
        "views/product_classification_views.xml",
        "views/product_product_views.xml",
        "views/website_sale_templates_views.xml",
        "views/res_config_settings_views.xml",
    ],

    'assets': {
        'web.assets_frontend': [
            'product_compatibility_filter/static/src/js/unselect_option.js',
        ],
    },

    "author": "Odoo Inc",

    "website": "https://www.odoo.com",
    
    "application": False,
}
