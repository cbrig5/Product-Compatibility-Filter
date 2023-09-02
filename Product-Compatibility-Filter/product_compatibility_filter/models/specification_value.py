from odoo import api, models, fields


class SpecificationValue(models.Model):
    _name = "specification.value"
    _description = "Specification Value"

    name = fields.Char(string="Specification Value", required="True")

    _sql_constraints = [
        ("name_uniq", "unique (name)", "Specification Value already exists!"),
    ]
