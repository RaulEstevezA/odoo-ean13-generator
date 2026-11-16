from odoo import _, api, models
from odoo.exceptions import AccessError, UserError, ValidationError


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


    @api.model
    def _check_ean13_generation_access(self):
        """Comprueba que el usuario pueda generar códigos EAN-13."""
        if not self.env.user.has_group(
            "product_ean13_generator.group_ean13_generator"
        ):
            raise AccessError(
                _("No tiene permisos para generar códigos EAN-13.")
            )


    def _validate_ean13_generation(self):
        """Valida que el producto pueda recibir un EAN-13 generado."""
        self.ensure_one()

        if self.barcode:
            raise UserError(
                _("La variante ya tiene un código de barras asignado.")
            )

        if not self.company_id:
            raise UserError(
                _("La variante debe estar asociada a una empresa.")
            )

        if not self.company_id.ean_generation_enabled:
            raise UserError(
                _(
                    "La generación de códigos EAN-13 no está habilitada "
                    "para la empresa %(company)s.",
                    company=self.company_id.display_name,
                )
            )

        if not self.company_id.ean_sequence_id:
            raise UserError(
                _(
                    "La empresa %(company)s no tiene configurada una "
                    "secuencia EAN-13.",
                    company=self.company_id.display_name,
                )
            )

