from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


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
