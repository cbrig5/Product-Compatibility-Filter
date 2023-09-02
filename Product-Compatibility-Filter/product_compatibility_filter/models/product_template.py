from collections import Counter
from operator import itemgetter
from xml.dom import ValidationErr
from odoo import api, models, fields, _, SUPERUSER_ID, http
from odoo.addons.http_routing.models.ir_http import unslug


class ProductTemplate(models.Model):
    _inherit = "product.template"

    is_part = fields.Boolean(string="Part")

    products = fields.Many2many(
        "product.template",
        string="Potential Compatible Products",
        compute="_get_products",
    )
    compatible_prods = fields.Many2many(
        "product.template",
        "compat_prods",
        "prod1",
        "prod2",
        string="Compatible Products",
        store=True,
        readonly=False,
        compute="_compute_compatible_prods",
    )

    # Products related fields
    product_classification = fields.Many2one(
        "product.classification",
        string="Product Class",
        help="A classification that this product belongs to for filtering in the eCommerce platform",
    )

    # Parts related fields
    part_compatibility = fields.Many2many(
        "product.classification",
        string="Compatible For",
        readonly=False,
        help="Classifications of products that this part is compatible for",
    )
    part_compatibility_status = fields.Boolean(
        compute="_compute_part_compatibility_status"
    )

    related_product_specification_names = fields.Many2many(
        "specification.name",
        compute="_compute_related_product_specification_names",
        readonly=False,
        string="Specification Names",
    )
    related_part_specification_names = fields.Many2many(
        "specification.name",
        compute="_compute_related_part_specification_names",
        readonly=False,
        string="Specification Names",
    )

    product_specification_line = fields.One2many(
        "specification.line", "template_id", string="Specification Line"
    )

    part_specification_line = fields.One2many(
        "specification.line", "template_id", string="Specification Line"
    )

    @api.onchange("related_product_specification_names")
    def _onchange_related_product_specification_names(self):
        if self.related_product_specification_names:
            spec_ids = self.related_product_specification_names.ids
            if self.product_classification:
                self.product_classification.specification_names = [(6, 0, spec_ids)]

    @api.depends("part_compatibility.specification_names")
    def _compute_related_part_specification_names(self):
        for record in self:
            related_spec_names = record.part_compatibility.specification_names
            record.related_part_specification_names = related_spec_names

    @api.depends("product_classification.specification_names")
    def _compute_related_product_specification_names(self):
        for record in self:
            related_spec_names = record.product_classification.specification_names
            record.related_product_specification_names = related_spec_names

    @api.depends(
        "part_compatibility",
        "product_classification",
        "part_specification_line",
        "product_specification_line",
    )
    def _get_products(self):
        """Gets the products that are compatible with the current part."""
        for record in self:
            product_template = self.env["product.template"]

            if record.part_compatibility:
                compatible_prods = []

                if record.part_specification_line:
                    for line in record.part_specification_line:
                        line_ids = (self.env["specification.line"].search(
                                [(
                                    "product_specification_name_id",
                                    "=",
                                    line.part_specification_name_id.id,
                                ),
                                (
                                    "product_specification_value_id",
                                    "in",
                                    line.part_specification_value_id.ids,
                                )]
                            )
                            .ids
                        )
                        prod_objs = product_template.search(
                            [("product_specification_line.id", "in", line_ids)]
                        )

                        compatible_prods.append(prod_objs)

                    if len(compatible_prods) == 1 and compatible_prods[0] == []:
                        compatible_prods = []

                    common_prod_ids = list(
                        set.intersection(
                            *[
                                set(prod.ids)
                                for prod in compatible_prods
                                if compatible_prods
                            ]
                        )
                    )
                    record.products = product_template.search(
                        [("id", "in", common_prod_ids)]
                    )

                else:
                    record.products = self.env["product.template"].search(
                        [(
                            "product_classification",
                            "in",
                            record.part_compatibility.ids,
                        )]
                    )

            else:
                record.products = None

    def _update_compatible_prods(self, record):
        compatible_prods = [
            prod.id for prod in record.compatible_prods if prod in record.products
        ]
        return compatible_prods or None

    # allows for auto updating of compatible products
    @api.depends(
        "part_compatibility",
        "product_classification",
        "part_specification_line",
        "product_specification_line",
    )
    def _compute_compatible_prods(self):
        """Updates the selected compatible products list when there is an update to a product or part."""
        for record in self:
            if record.is_part and record.part_specification_line:
                record.compatible_prods = self._update_compatible_prods(record)
            elif not record.is_part:
                part_recs = self.env["product.template"].search(
                    [("is_part", "=", True)]
                )
                for part_rec in part_recs:
                    part_rec.compatible_prods = self._update_compatible_prods(part_rec)

    @api.depends("part_compatibility")
    def _compute_part_compatibility_status(self):
        for record in self:
            record.part_compatibility_status = (
                True if record.part_compatibility else False
            )

    def get_variants(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Variants",
            "view_mode": "tree,form",
            "res_model": "product.product",
            "domain": [("name", "=", self.name)],
        }

    # eCommerce qWeb functions
    @api.model
    def _search_get_detail(self, website, order, options):
        """Adds the part compatibility and product specification values to the search domain."""
        results = super(ProductTemplate, self)._search_get_detail(
            website, order, options
        )
        domains = results["base_domain"]

        compat_parts = options.get("compat_parts")
        if compat_parts:
            domains.append([("product_variant_ids", "=", compat_parts)])

        classification = options.get("classification")
        if classification:
            domains.append([("part_compatibility", "=", unslug(classification)[1])])

        prod_id = options.get("prod_id")
        if prod_id:
            domains.append([("compatible_prods", "=", unslug(prod_id)[1])])

        specs_values = options.get("specs_values")
        if specs_values and not prod_id:
            specs = None
            ids = []
            for value in specs_values:
                if not specs:
                    specs = value[0]
                    ids.append(value[1])
                elif value[0] == specs:
                    ids.append(value[1])
                else:
                    specification_lines = self.env["specification.line"].search(
                        [
                            ("part_specification_name_id", "=", specs),
                            ("part_specification_value_id", "in", ids),
                        ]
                    )
                    domains.append(
                        [("part_specification_line", "in", specification_lines.ids)]
                    )
                    specs = value[0]
                    ids = [value[1]]
            if specs:
                specification_lines = self.env["specification.line"].search(
                    [
                        ("part_specification_name_id", "=", specs),
                        ("part_specification_value_id", "in", ids),
                    ]
                )
                domains.append(
                    [("part_specification_line", "in", specification_lines.ids)]
                )

        results.update(base_domain=domains)
        return results

    def _get_all_compatible_variants(self, variants):
        res = []
        for variant in variants:
            variant = int(variant)
            compatible_parts = self.env["product.product"].search(
                [("compatible_prods.product_template_variant_value_ids", "=", variant)]
            )
            res = []
            for part in compatible_parts:
                to_append = ""
                for attr in part.product_template_variant_value_ids:
                    to_append += attr.display_name + " | "
                res.append(to_append)
        return res
