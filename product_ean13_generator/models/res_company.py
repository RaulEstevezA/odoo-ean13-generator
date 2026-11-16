from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    ean_generation_enabled = fields.Boolean(
        string="Permitir generación de EAN-13",
        default=False,
        help="Indica si esta empresa permite generar códigos EAN-13.",
    )

    ean_sequence_id = fields.Many2one(
        comodel_name="ir.sequence",
        string="Secuencia EAN-13",
        check_company=True,
        ondelete="restrict",
        help="Secuencia utilizada para generar la base numérica del código EAN-13.",
    )