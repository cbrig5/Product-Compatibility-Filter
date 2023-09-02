from odoo import api, models, fields


class SpecificationLine(models.Model):
    _name = 'specification.line'
    _description = 'Specification Line'

    template_id = fields.Many2one(
        'product.template', string="Product Template", required=True
    )

    product_specification_name_id = fields.Many2one(
        'specification.name',
        string="Product Specification Name",
    )

    product_specification_value_id = fields.Many2one(
        'specification.value',
        string="Product Specification Value",
    )

    part_specification_name_id = fields.Many2one(
        'specification.name',
        string="Part Specification Name",
    )

    part_specification_value_id = fields.Many2many(
        'specification.value',
        string="Part Specification Value",
    )
