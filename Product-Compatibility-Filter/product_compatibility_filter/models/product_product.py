from odoo import api, models, fields


class ProductProduct(models.Model):
    _inherit = 'product.product'

    is_part = fields.Boolean(readonly=True, related='product_tmpl_id.is_part')

    products = fields.Many2many(
        'product.product', string="products", compute='_get_products'
    )
    compatible_prods = fields.Many2many(
        'product.product', 'compat_vars', 'var1', 'var2', string="Compatible Products"
    )

    # Product related
    product_classification = fields.Many2one(
        related='product_tmpl_id.product_classification',
        help="A classification that this product belongs to for filtering in the eCommerce platform",
    )

    # Part related
    part_compatibility = fields.Many2many(
        related='product_tmpl_id.part_compatibility',
        help="Classifications of products that this part is compatible for",
    )
    part_compatibility_status = fields.Boolean(
        related='product_tmpl_id.part_compatibility_status'
    )

    # Classification string
    classification = fields.Char(
        string="Part/Product Class",
        compute='_compute_classification',
        help="display either product classification or part compatibility",
    )

    @api.depends('is_part', 'product_classification', 'part_compatibility')
    def _compute_classification(self):
        """Display either product classification or part compatibility"""
        for product in self:
            if product.is_part:
                part_compatibility = product.part_compatibility
                if len(part_compatibility) > 1:
                    product.classification = ', '.join(
                        part_comp.name for part_comp in part_compatibility
                    )
                else:
                    product.classification = part_compatibility.name
            else:
                product.classification = product.product_classification.name

    @api.depends('part_compatibility', 'product_classification')
    def _get_products(self):
        """Get all products that are compatible with this part"""
        for record in self:
            if record.part_compatibility:
                # Search all COMPATIBLE products for a part
                # Look for all of their variants
                record.products = self.env['product.product'].search([
                    ('id', 'in', record.product_tmpl_id.compatible_prods.product_variant_ids.ids,)]
                )
            else:
                record.products = None
    