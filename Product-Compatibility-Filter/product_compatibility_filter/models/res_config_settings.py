from odoo import fields, models, api


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    filter_by = fields.Selection(
        [
            ("specifications", "Specifications"),
            ("variants", "Variants"),
        ],
        required=True,
        string="Filter by:",
    )

    # Set the default value to "specifications" only when filter_by is not set
    def default_get(self, fields_list):
        defaults = super(ResConfigSettings, self).default_get(fields_list)
        if defaults["filter_by"] == False:
            defaults["filter_by"] = "specifications"
        return defaults

    @api.model
    def set_values(self):
        super(ResConfigSettings, self).set_values()
        self.env["ir.config_parameter"].set_param(
            "product_compatibility_filter.filter_by", self.filter_by
        )

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        params = self.env["ir.config_parameter"].sudo()
        res.update(filter_by=params.get_param("product_compatibility_filter.filter_by"))
        return res
