from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

EAN13_BASE_LENGTH = 12


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
        domain="[('company_id', 'in', [False, id])]",
        ondelete="restrict",
        help=(
            "Secuencia utilizada para generar la base numérica del código "
            "EAN-13. Debe producir exactamente 12 dígitos: prefijo y sufijo "
            "numéricos (o vacíos) y prefijo + relleno + sufijo = 12."
        ),
    )

    @api.constrains("ean_sequence_id")
    def _check_ean_sequence_id(self):
        for company in self:
            company._raise_if_invalid_ean13_sequence(ValidationError)

    def _get_ean13_sequence_errors(self):
        """Devuelve los motivos por los que la secuencia EAN-13 no es válida.

        Una lista vacía indica que la secuencia es válida (o que no hay
        secuencia configurada, caso que se valida por separado).
        """
        self.ensure_one()
        sequence = self.ean_sequence_id
        if not sequence:
            return []

        errors = []
        prefix = sequence.prefix or ""
        suffix = sequence.suffix or ""

        if sequence.company_id and sequence.company_id != self:
            errors.append(
                _(
                    "La secuencia pertenece a otra empresa (%(company)s).",
                    company=sequence.company_id.display_name,
                )
            )

        if sequence.use_date_range:
            errors.append(
                _(
                    "La secuencia no puede usar subsecuencias por rango de "
                    "fechas, ya que reiniciaría la numeración."
                )
            )

        if prefix and not (prefix.isascii() and prefix.isdigit()):
            errors.append(
                _(
                    "El prefijo '%(prefix)s' solo puede contener dígitos.",
                    prefix=prefix,
                )
            )

        if suffix and not (suffix.isascii() and suffix.isdigit()):
            errors.append(
                _(
                    "El sufijo '%(suffix)s' solo puede contener dígitos.",
                    suffix=suffix,
                )
            )

        total_length = len(prefix) + sequence.padding + len(suffix)
        if total_length != EAN13_BASE_LENGTH:
            errors.append(
                _(
                    "Prefijo (%(prefix)s) + relleno (%(padding)s) + sufijo "
                    "(%(suffix)s) suman %(total)s dígitos y deben sumar "
                    "%(expected)s.",
                    prefix=len(prefix),
                    padding=sequence.padding,
                    suffix=len(suffix),
                    total=total_length,
                    expected=EAN13_BASE_LENGTH,
                )
            )
        elif sequence.number_next_actual >= 10**sequence.padding:
            errors.append(
                _(
                    "La secuencia está agotada: el siguiente número "
                    "(%(number)s) no cabe en %(padding)s dígitos.",
                    number=sequence.number_next_actual,
                    padding=sequence.padding,
                )
            )

        return errors

    def _raise_if_invalid_ean13_sequence(self, exception_class):
        """Lanza ``exception_class`` con todos los errores de la secuencia."""
        self.ensure_one()
        errors = self._get_ean13_sequence_errors()
        if errors:
            raise exception_class(
                _(
                    "La secuencia EAN-13 '%(sequence)s' de la empresa "
                    "%(company)s no es válida:\n%(errors)s",
                    sequence=self.ean_sequence_id.display_name,
                    company=self.display_name,
                    errors="\n".join(f"- {error}" for error in errors),
                )
            )
