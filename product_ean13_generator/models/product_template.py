from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ProductTemplate(models.Model):
    _inherit = "product.template"

    can_generate_ean13 = fields.Boolean(
        compute="_compute_can_generate_ean13",
    )

    @api.depends(
        "product_variant_count",
        "product_variant_ids.can_generate_ean13",
    )
    def _compute_can_generate_ean13(self):
        """Solo disponible si la plantilla tiene una única variante.

        Con varias variantes no es posible determinar a cuál asignar el
        código, por lo que la generación debe hacerse desde cada variante.
        """
        for template in self:
            template.can_generate_ean13 = bool(
                template.product_variant_count == 1
                and template.product_variant_id.can_generate_ean13
            )

    def action_generate_ean13(self):
        """Genera el EAN-13 de la única variante de la plantilla."""
        self.ensure_one()

        if self.product_variant_count != 1:
            raise UserError(
                _(
                    "El producto %(product)s tiene varias variantes. "
                    "Genere el código EAN-13 desde cada variante.",
                    product=self.display_name,
                )
            )

        return self.product_variant_id.action_generate_ean13()
