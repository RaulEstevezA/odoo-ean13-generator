from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase, new_test_user


@tagged("post_install", "-at_install")
class TestEan13Generation(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product_model = cls.env["product.product"]

    def test_calculate_known_check_digit(self):
        check_digit = self.product_model._calculate_ean13_check_digit("400638133393")

        self.assertEqual(check_digit, "1")

    def test_calculate_zero_check_digit(self):
        check_digit = self.product_model._calculate_ean13_check_digit("000000000000")

        self.assertEqual(check_digit, "0")

    def test_reject_invalid_bases(self):
        invalid_bases = [
            "123",
            "12345678901A",
            "１２３４５６７８９０１２",
            123456789012,
        ]

        for base in invalid_bases:
            with self.subTest(base=base), self.assertRaises(ValidationError):
                self.product_model._calculate_ean13_check_digit(base)

    def test_generate_ean13_from_sequence(self):
        sequence = self.env["ir.sequence"].create(
            {
                "name": "Secuencia EAN-13 de prueba",
                "implementation": "no_gap",
                "padding": 12,
                "number_next": 1,
                "company_id": self.env.company.id,
            }
        )

        ean13 = self.product_model._generate_ean13_from_sequence(sequence)

        self.assertEqual(ean13, "0000000000017")

    def test_reject_product_with_existing_barcode(self):
        product = self.env["product.product"].create(
            {
                "name": "Producto con código",
                "barcode": "1234567890128",
            }
        )

        with self.assertRaises(UserError):
            product._validate_ean13_generation()

    def test_reject_product_without_company(self):
        product = self.env["product.product"].create(
            {
                "name": "Producto sin empresa",
                "company_id": False,
            }
        )

        with self.assertRaises(UserError):
            product._validate_ean13_generation()

    def test_reject_generation_when_disabled(self):
        company = self.env.company
        company.ean_generation_enabled = False

        product = self.env["product.product"].create(
            {
                "name": "Producto con generación desactivada",
                "company_id": company.id,
            }
        )

        with self.assertRaises(UserError):
            product._validate_ean13_generation()

    def test_reject_generation_without_sequence(self):
        company = self.env.company
        company.write(
            {
                "ean_generation_enabled": True,
                "ean_sequence_id": False,
            }
        )

        product = self.env["product.product"].create(
            {
                "name": "Producto sin secuencia EAN-13",
                "company_id": company.id,
            }
        )

        with self.assertRaises(UserError):
            product._validate_ean13_generation()

    def test_accept_product_with_valid_configuration(self):
        company = self.env.company

        sequence = self.env["ir.sequence"].create(
            {
                "name": "Secuencia EAN-13 válida",
                "implementation": "no_gap",
                "padding": 12,
                "number_next": 1,
                "company_id": company.id,
            }
        )

        company.write(
            {
                "ean_generation_enabled": True,
                "ean_sequence_id": sequence.id,
            }
        )

        product = self.env["product.product"].create(
            {
                "name": "Producto preparado para generar EAN-13",
                "company_id": company.id,
            }
        )

        result = product._validate_ean13_generation()

        self.assertIsNone(result)

    def test_reject_user_without_generation_group(self):
        user = new_test_user(
            self.env,
            login="ean13_user_without_permission",
            groups="base.group_user",
        )

        with self.assertRaises(AccessError):
            self.product_model.with_user(
                user
            )._check_ean13_generation_access()

    def test_accept_user_with_generation_group(self):
        user = new_test_user(
            self.env,
            login="ean13_user_with_permission",
            groups=(
                "base.group_user,"
                "product_ean13_generator.group_ean13_generator"
            ),
        )

        result = self.product_model.with_user(
            user
        )._check_ean13_generation_access()

        self.assertIsNone(result)
