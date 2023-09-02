from odoo import api, fields, models


class ProductClassification(models.Model):
    _name = "product.classification"
    _description = "Product Classification"

    name = fields.Char(required=True, store=True, string="Classification Name")

    specification_names = fields.Many2many(
        "specification.name", string="Specification Names"
    )

    product_template_ids = fields.Many2many(
        "product.template",
        string="Product Template IDs",
    )

    product_ids = fields.Many2many("product.product", string="Product IDs")

    # SQL constraint for unique classification name
    _sql_constraints = [
        ("name_uniq", "unique (name)", "Classification name already exists!"),
    ]
