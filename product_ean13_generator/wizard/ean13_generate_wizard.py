from odoo import Command, api, fields, models


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