from odoo import models


class Ean13GenerateWizard(models.TransientModel):
    _name = "ean13.generate.wizard"
    _description = "Generación masiva de códigos EAN-13"