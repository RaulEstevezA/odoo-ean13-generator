from odoo import api, models
from odoo.exceptions import ValidationError


class IrSequence(models.Model):
    _inherit = "ir.sequence"

    @api.constrains(
        "prefix",
        "suffix",
        "padding",
        "use_date_range",
        "company_id",
        "number_next",
    )
    def _check_ean13_sequence_configuration(self):
        """Impide dejar inválida una secuencia que ya se usa para EAN-13."""
        companies = (
            self.env["res.company"]
            .sudo()
            .search([("ean_sequence_id", "in", self.ids)])
        )
        for company in companies:
            company._raise_if_invalid_ean13_sequence(ValidationError)
