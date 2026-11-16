from odoo.tests.common import TransactionCase


class Ean13TestCommon(TransactionCase):
    """Base común para los tests de generación de EAN-13.

    Aísla los tests de los códigos de barras que ya existan en la base de
    datos, para que los valores esperados sean deterministas.

    La limpieza se ejecuta dentro de la transacción de la clase de test y
    Odoo la revierte al finalizar: no se persiste ningún cambio.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["product.product"].with_context(active_test=False).search(
            [("barcode", "!=", False)]
        ).write({"barcode": False})
        cls.env["product.packaging"].search(
            [("barcode", "!=", False)]
        ).write({"barcode": False})
