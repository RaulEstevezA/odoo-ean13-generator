from odoo import Command
from odoo.tests import tagged
from odoo.tests.common import new_test_user

from .common import Ean13TestCommon


@tagged("post_install", "-at_install")
class TestEan13GenerateWizard(Ean13TestCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.main_company = cls.env.company
        cls.other_company = cls.env["res.company"].create(
            {
                "name": "Empresa secundaria EAN-13 de prueba",
            }
        )

        cls.main_sequence = cls.env["ir.sequence"].create(
            {
                "name": "Secuencia EAN-13 empresa principal",
                "implementation": "no_gap",
                "prefix": "8",
                "padding": 11,
                "number_next": 1,
                "company_id": cls.main_company.id,
            }
        )

        cls.other_sequence = cls.env["ir.sequence"].create(
            {
                "name": "Secuencia EAN-13 empresa secundaria",
                "implementation": "no_gap",
                "prefix": "9",
                "padding": 11,
                "number_next": 1,
                "company_id": cls.other_company.id,
            }
        )

        cls.main_company.write(
            {
                "ean_generation_enabled": True,
                "ean_sequence_id": cls.main_sequence.id,
            }
        )
        cls.other_company.write(
            {
                "ean_generation_enabled": True,
                "ean_sequence_id": cls.other_sequence.id,
            }
        )

        cls.user = new_test_user(
            cls.env,
            login="ean13_mass_generator",
            groups=(
                "base.group_user,"
                "product_ean13_generator.group_ean13_generator"
            ),
        )
        cls.user.write(
            {
                "company_ids": [
                    Command.set(
                        [
                            cls.main_company.id,
                            cls.other_company.id,
                        ]
                    )
                ],
                "company_id": cls.main_company.id,
            }
        )

        cls.main_product = cls.env["product.product"].create(
            {
                "name": "Producto EAN empresa principal",
                "company_id": cls.main_company.id,
            }
        )

        cls.other_product = cls.env["product.product"].create(
            {
                "name": "Producto EAN empresa secundaria",
                "company_id": cls.other_company.id,
            }
        )

        cls.product_with_barcode = cls.env["product.product"].create(
            {
                "name": "Producto con EAN existente",
                "company_id": cls.main_company.id,
                "barcode": "7000000000003",
            }
        )


    def test_mass_generation_with_multiple_companies_and_errors(self):
        products = (
            self.main_product
            | self.other_product
            | self.product_with_barcode
        )

        wizard = (
            self.env["ean13.generate.wizard"]
            .with_user(self.user)
            .with_context(
                active_model="product.product",
                active_ids=products.ids,
                allowed_company_ids=[
                    self.main_company.id,
                    self.other_company.id,
                ],
            )
            .create({})
        )

        self.assertEqual(
            set(wizard.product_ids.ids),
            set(products.ids),
        )

        wizard.action_generate_ean13()

        self.main_product.invalidate_recordset(["barcode"])
        self.other_product.invalidate_recordset(["barcode"])
        self.product_with_barcode.invalidate_recordset(["barcode"])

        self.assertEqual(wizard.state, "done")
        self.assertEqual(wizard.success_count, 2)
        self.assertEqual(wizard.error_count, 1)

        self.assertEqual(
            self.main_product.barcode,
            "8000000000019",
        )
        self.assertEqual(
            self.other_product.barcode,
            "9000000000018",
        )
        self.assertEqual(
            self.product_with_barcode.barcode,
            "7000000000003",
        )
