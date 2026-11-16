from odoo.exceptions import UserError
from odoo.tests import tagged

from ..hooks import pre_init_hook
from .common import Ean13TestCommon


@tagged("post_install", "-at_install")
class TestEan13InstallHook(Ean13TestCommon):
    def test_install_allowed_without_duplicates(self):
        self.env["product.product"].create(
            {"name": "Producto con código único", "barcode": "4006381333931"}
        )

        self.assertIsNone(pre_init_hook(self.env))

    def test_install_blocked_with_duplicates(self):
        # Simula una base de datos previa a la instalación, en la que todavía
        # no existe la restricción de unicidad global. PostgreSQL revierte
        # también este cambio de esquema al finalizar la transacción del test.
        self.env.cr.execute(
            "ALTER TABLE product_product "
            "DROP CONSTRAINT product_product_barcode_global_unique"
        )

        # Odoo permite el mismo código en empresas distintas.
        other_company = self.env["res.company"].create(
            {"name": "Empresa con código duplicado"}
        )
        first = self.env["product.product"].create(
            {
                "name": "Primera variante duplicada",
                "company_id": self.env.company.id,
                "barcode": "4006381333931",
            }
        )
        second = self.env["product.product"].create(
            {
                "name": "Segunda variante duplicada",
                "company_id": other_company.id,
                "barcode": "4006381333931",
                "active": False,
            }
        )

        with self.assertRaises(UserError) as error:
            pre_init_hook(self.env)

        message = str(error.exception)
        self.assertIn("4006381333931", message)
        self.assertIn(f"ID {first.id}", message)
        self.assertIn(f"ID {second.id}", message)
