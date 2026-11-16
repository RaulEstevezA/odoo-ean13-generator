from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tests.common import new_test_user

from .common import Ean13TestCommon


@tagged("post_install", "-at_install")
class TestEan13Template(Ean13TestCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.company = cls.env.company
        sequence = cls.env["ir.sequence"].create(
            {
                "name": "Secuencia EAN-13 para plantillas",
                "implementation": "no_gap",
                "prefix": "5",
                "padding": 11,
                "number_next": 1,
                "company_id": cls.company.id,
            }
        )
        cls.company.write(
            {
                "ean_generation_enabled": True,
                "ean_sequence_id": sequence.id,
            }
        )

        cls.user = new_test_user(
            cls.env,
            login="ean13_template_generator",
            groups=(
                "base.group_user,"
                "product_ean13_generator.group_ean13_generator"
            ),
        )

        cls.single_variant_template = cls.env["product.template"].create(
            {
                "name": "Plantilla con una variante",
                "company_id": cls.company.id,
            }
        )

        attribute = cls.env["product.attribute"].create(
            {
                "name": "Color de prueba EAN-13",
                "value_ids": [
                    Command.create({"name": "Rojo"}),
                    Command.create({"name": "Azul"}),
                ],
            }
        )
        cls.multi_variant_template = cls.env["product.template"].create(
            {
                "name": "Plantilla con varias variantes",
                "company_id": cls.company.id,
                "attribute_line_ids": [
                    Command.create(
                        {
                            "attribute_id": attribute.id,
                            "value_ids": [Command.set(attribute.value_ids.ids)],
                        }
                    ),
                ],
            }
        )

    def test_can_generate_with_single_variant(self):
        self.assertTrue(self.single_variant_template.can_generate_ean13)

    def test_cannot_generate_with_multiple_variants(self):
        self.assertEqual(self.multi_variant_template.product_variant_count, 2)
        self.assertFalse(self.multi_variant_template.can_generate_ean13)

    def test_generate_from_template_assigns_variant_barcode(self):
        self.single_variant_template.with_user(self.user).action_generate_ean13()

        variant = self.single_variant_template.product_variant_id
        self.assertEqual(variant.barcode, "5000000000012")
        self.assertEqual(self.single_variant_template.barcode, variant.barcode)

    def test_generate_from_template_with_multiple_variants_raises(self):
        with self.assertRaises(UserError):
            self.multi_variant_template.with_user(
                self.user
            ).action_generate_ean13()

    def test_generate_from_template_reuses_variant_validations(self):
        self.single_variant_template.barcode = "4006381333931"

        self.assertFalse(self.single_variant_template.can_generate_ean13)
        with self.assertRaises(UserError):
            self.single_variant_template.with_user(
                self.user
            ).action_generate_ean13()

    def test_button_in_template_form_only_for_group(self):
        view = self.env.ref("product.product_template_only_form_view")
        user_without_group = new_test_user(
            self.env,
            login="ean13_template_without_group",
            groups="base.group_user",
        )

        arch_with_group = (
            self.env["product.template"]
            .with_user(self.user)
            .get_view(view_id=view.id, view_type="form")["arch"]
        )
        arch_without_group = (
            self.env["product.template"]
            .with_user(user_without_group)
            .get_view(view_id=view.id, view_type="form")["arch"]
        )

        self.assertIn('name="action_generate_ean13"', arch_with_group)
        self.assertNotIn('name="action_generate_ean13"', arch_without_group)
