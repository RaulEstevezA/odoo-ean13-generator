from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    ean_generation_enabled = fields.Boolean(
        related="company_id.ean_generation_enabled",
        readonly=False,
    )

    ean_sequence_id = fields.Many2one(
        related="company_id.ean_sequence_id",
        readonly=False,
        domain="[('company_id', 'in', [False, company_id])]",
    )
