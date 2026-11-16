from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged
from odoo.tests.common import new_test_user

from .common import Ean13TestCommon


@tagged("post_install", "-at_install")
class TestEan13SequenceConfig(Ean13TestCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company

    def _create_sequence(self, **values):
        return self.env["ir.sequence"].create(
            {
                "name": "Secuencia EAN-13 de configuración",
                "implementation": "no_gap",
                "padding": 12,
                "number_next": 1,
                "company_id": self.company.id,
                **values,
            }
        )

    def _assign(self, sequence):
        self.company.write(
            {
                "ean_generation_enabled": True,
                "ean_sequence_id": sequence.id,
            }
        )

    def test_accept_valid_sequences(self):
        valid_values = [
            {"padding": 12},
            {"prefix": "84", "padding": 10},
            {"prefix": "8", "padding": 9, "suffix": "00"},
            {"padding": 12, "company_id": False},
        ]

        for values in valid_values:
            with self.subTest(values=values):
                sequence = self._create_sequence(**values)
                self._assign(sequence)

                self.assertFalse(self.company._get_ean13_sequence_errors())

    def test_reject_invalid_sequences(self):
        other_company = self.env["res.company"].create(
            {"name": "Otra empresa EAN-13"}
        )
        invalid_values = {
            "prefijo no numérico": {"prefix": "WH/", "padding": 9},
            "sufijo no numérico": {"padding": 11, "suffix": "X"},
            "longitud incorrecta": {"padding": 5},
            "rango de fechas": {"use_date_range": True},
            "otra empresa": {"company_id": other_company.id},
            "secuencia agotada": {
                "prefix": "8400000",
                "padding": 5,
                "number_next": 10**5,
            },
        }

        for reason, values in invalid_values.items():
            with self.subTest(reason=reason):
                sequence = self._create_sequence(**values)

                with self.assertRaises(ValidationError):
                    self._assign(sequence)

    def test_reject_invalidating_sequence_in_use(self):
        sequence = self._create_sequence()
        self._assign(sequence)

        with self.assertRaises(ValidationError):
            sequence.write({"prefix": "WH/"})

    def test_unused_sequence_can_be_modified(self):
        sequence = self._create_sequence()

        sequence.write({"prefix": "WH/"})

        self.assertEqual(sequence.prefix, "WH/")

    def test_invalid_sequence_hides_action_and_is_not_consumed(self):
        sequence = self._create_sequence()
        self._assign(sequence)
        product = self.env["product.product"].create(
            {
                "name": "Producto con secuencia inválida",
                "company_id": self.company.id,
            }
        )
        user = new_test_user(
            self.env,
            login="ean13_invalid_sequence_user",
            groups=(
                "base.group_user,"
                "product_ean13_generator.group_ean13_generator"
            ),
        )
        self.assertTrue(product.can_generate_ean13)

        # Simula una secuencia que quedó inválida saltándose las
        # restricciones (p. ej. datos previos a la instalación del módulo).
        self.env.cr.execute(
            "UPDATE ir_sequence SET prefix = 'WH/' WHERE id = %s",
            [sequence.id],
        )
        sequence.invalidate_recordset(["prefix"])
        product.invalidate_recordset(["can_generate_ean13"])

        self.assertFalse(product.can_generate_ean13)
        with self.assertRaises(UserError):
            product.with_user(user).action_generate_ean13()
        self.assertEqual(sequence.number_next_actual, 1)
