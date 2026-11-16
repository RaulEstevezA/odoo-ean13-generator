from odoo import _, api, models
from odoo.exceptions import ValidationError


class ProductProduct(models.Model):
    _inherit = "product.product"

    @api.model
    def _calculate_ean13_check_digit(self, base):
        """Calcula el dígito de control de una base EAN-13 de 12 cifras."""
        if (
            not isinstance(base, str)
            or len(base) != 12
            or not base.isascii()
            or not base.isdigit()
        ):
            raise ValidationError(
                _("La base EAN-13 debe contener exactamente 12 dígitos.")
            )

        odd_sum = sum(int(base[index]) for index in range(0, 12, 2))
        even_sum = sum(int(base[index]) for index in range(1, 12, 2))
        weighted_sum = odd_sum + (even_sum * 3)

        return str((10 - (weighted_sum % 10)) % 10)
        
    @api.model
    def _generate_ean13_from_sequence(self, sequence):
        """Genera un EAN-13 completo utilizando una secuencia configurada."""
        sequence.ensure_one()

        base = sequence.next_by_id()
        check_digit = self._calculate_ean13_check_digit(base)

        return f"{base}{check_digit}"

