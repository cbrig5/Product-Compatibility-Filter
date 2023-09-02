from odoo import api, models, fields


class SpecificationName(models.Model):
    _name = 'specification.name'
    _description = 'Specification Name'

    name = fields.Char(string="Specification Names", required='True')
