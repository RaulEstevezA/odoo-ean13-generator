from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase, new_test_user
from psycopg2.errors import UniqueViolation
from unittest.mock import patch


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

    def test_action_generate_ean13(self):
        company = self.env.company

        sequence = self.env["ir.sequence"].create(
            {
                "name": "Secuencia para generación individual",
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
                "name": "Producto con EAN-13 generado",
                "company_id": company.id,
            }
        )

        user = new_test_user(
            self.env,
            login="ean13_individual_generator",
            groups=(
                "base.group_user,"
                "product_ean13_generator.group_ean13_generator"
            ),
        )

        product.with_user(user).action_generate_ean13()

        self.assertEqual(product.barcode, "0000000000017")

    def test_reject_ean13_assigned_to_another_product(self):
        ean13 = "0000000000017"

        self.env["product.product"].create(
            {
                "name": "Producto con EAN-13 existente",
                "barcode": ean13,
            }
        )

        with self.assertRaises(UserError):
            self.product_model._check_ean13_availability(ean13)

    def test_reject_ean13_assigned_to_packaging(self):
        ean13 = "0000000000017"
        company = self.env.company

        product = self.env["product.product"].create(
            {
                "name": "Producto con embalaje",
                "company_id": company.id,
            }
        )

        self.env["product.packaging"].create(
            {
                "name": "Caja de prueba",
                "product_id": product.id,
                "company_id": company.id,
                "barcode": ean13,
            }
        )

        with self.assertRaises(UserError):
            self.product_model._check_ean13_availability(ean13)

    def test_reject_duplicate_barcode_across_companies(self):
        ean13 = "0000000000017"

        other_company = self.env["res.company"].create(
            {
                "name": "Segunda empresa de prueba",
            }
        )

        self.env["product.product"].create(
            {
                "name": "Producto de la empresa principal",
                "company_id": self.env.company.id,
                "barcode": ean13,
            }
        )

        with self.assertRaises(UniqueViolation), self.env.cr.savepoint():
            self.env["product.product"].create(
                {
                    "name": "Producto de la segunda empresa",
                    "company_id": other_company.id,
                    "barcode": ean13,
                }
            )

    def test_concurrent_duplicate_returns_user_error(self):
        company = self.env.company

        sequence = self.env["ir.sequence"].create(
            {
                "name": "Secuencia para colisión concurrente",
                "implementation": "no_gap",
                "prefix": "6",
                "padding": 11,
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

        self.env["product.product"].create(
            {
                "name": "Producto con código concurrente",
                "company_id": company.id,
                "barcode": "6000000000011",
            }
        )

        product = self.env["product.product"].create(
            {
                "name": "Producto que sufre la colisión",
                "company_id": company.id,
            }
        )

        user = new_test_user(
            self.env,
            login="ean13_concurrent_generator",
            groups=(
                "base.group_user,"
                "product_ean13_generator.group_ean13_generator"
            ),
        )

        with patch.object(
            type(self.product_model),
            "_check_ean13_availability",
            return_value=None,
        ):
            with self.assertRaises(UserError):
                product.with_user(user).action_generate_ean13()

        self.assertFalse(product.barcode)
