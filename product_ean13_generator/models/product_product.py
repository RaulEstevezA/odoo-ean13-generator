from psycopg2.errors import UniqueViolation

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError



class ProductProduct(models.Model):
    _inherit = "product.product"

    _sql_constraints = [
        (
            "barcode_global_unique",
            "UNIQUE(barcode)",
            "El código de barras debe ser único en todo el sistema.",
        ),
    ]

    can_generate_ean13 = fields.Boolean(
        compute="_compute_can_generate_ean13",
    )


    @api.depends(
        "barcode",
        "company_id",
        "company_id.ean_generation_enabled",
        "company_id.ean_sequence_id",
    )
    def _compute_can_generate_ean13(self):
        """Indica si la variante cumple las condiciones funcionales."""
        for product in self:
            company = product.company_id
            product.can_generate_ean13 = bool(
                not product.barcode
                and company
                and company.ean_generation_enabled
                and company.ean_sequence_id
            )
            

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


    @api.model
    def _check_ean13_availability(self, ean13):
        """Comprueba que el EAN-13 no esté utilizado en el sistema."""
        product_exists = self.sudo().search_count(
            [("barcode", "=", ean13)],
            limit=1,
        )

        if product_exists:
            raise UserError(
                _("El código EAN-13 ya está asignado a otra variante.")
            )

        packaging_exists = self.env["product.packaging"].sudo().search_count(
            [("barcode", "=", ean13)],
            limit=1,
        )

        if packaging_exists:
            raise UserError(
                _("El código EAN-13 ya está asignado a un embalaje.")
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


    def action_generate_ean13(self):
        """Genera y asigna un EAN-13 a una variante."""
        self.ensure_one()

        self._check_ean13_generation_access()
        self._validate_ean13_generation()

        sequence = self.company_id.ean_sequence_id
        ean13 = self._generate_ean13_from_sequence(sequence)

        self._check_ean13_availability(ean13)

        try:
            with self.env.cr.savepoint():
                self.sudo().write({"barcode": ean13})
        except UniqueViolation as error:
            if (
                error.diag.constraint_name
                != "product_product_barcode_global_unique"
            ):
                raise

            raise UserError(
                _(
                    "No se ha podido asignar el código EAN-13 porque "
                    "ya está siendo utilizado por otra variante."
                )
            ) from None

        return True
