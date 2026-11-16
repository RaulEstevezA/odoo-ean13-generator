from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError


class Ean13GenerateWizard(models.TransientModel):
    _name = "ean13.generate.wizard"
    _description = "Generación masiva de códigos EAN-13"

    product_ids = fields.Many2many(
        comodel_name="product.product",
        string="Variantes seleccionadas",
        readonly=True,
    )

    state = fields.Selection(
        selection=[
            ("confirm", "Confirmación"),
            ("done", "Finalizado"),
        ],
        default="confirm",
        readonly=True,
    )

    success_count = fields.Integer(
        string="Generados correctamente",
        readonly=True,
    )

    error_count = fields.Integer(
        string="Errores",
        readonly=True,
    )

    result_details = fields.Text(
        string="Detalle del resultado",
        readonly=True,
    )


    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)

        active_model = self.env.context.get("active_model")
        active_ids = self.env.context.get("active_ids", [])

        if active_model == "product.product" and "product_ids" in fields_list:
            values["product_ids"] = [Command.set(active_ids)]

        return values


    def action_generate_ean13(self):
        self.ensure_one()

        if not self.product_ids:
            raise UserError(
                _("Debe seleccionar al menos una variante.")
            )

        success_lines = []
        error_lines = []

        for product in self.product_ids:
            try:
                with self.env.cr.savepoint():
                    product.action_generate_ean13()

                success_lines.append(
                    _(
                        "OK - %(product)s: %(ean13)s",
                        product=product.display_name,
                        ean13=product.barcode,
                    )
                )
            except UserError as error:
                error_lines.append(
                    _(
                        "ERROR - %(product)s: %(message)s",
                        product=product.display_name,
                        message=str(error),
                    )
                )

        self.write(
            {
                "state": "done",
                "success_count": len(success_lines),
                "error_count": len(error_lines),
                "result_details": "\n".join(success_lines + error_lines),
            }
        )

        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }