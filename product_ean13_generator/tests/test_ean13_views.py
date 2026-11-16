from odoo.tests import tagged
from odoo.tests.common import new_test_user

from .common import Ean13TestCommon

VARIANT_FORM_VIEWS = [
    "product.product_normal_form_view",
    "product.product_variant_easy_edit_view",
]


@tagged("post_install", "-at_install")
class TestEan13Views(Ean13TestCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.user_with_group = new_test_user(
            cls.env,
            login="ean13_view_user_with_group",
            groups=(
                "base.group_user,"
                "product_ean13_generator.group_ean13_generator"
            ),
        )
        cls.user_without_group = new_test_user(
            cls.env,
            login="ean13_view_user_without_group",
            groups="base.group_user",
        )

    def _get_variant_form_arch(self, user, view_xmlid):
        view = self.env.ref(view_xmlid)
        return (
            self.env["product.product"]
            .with_user(user)
            .get_view(view_id=view.id, view_type="form")["arch"]
        )

    def test_button_in_variant_forms_for_user_with_group(self):
        for view_xmlid in VARIANT_FORM_VIEWS:
            with self.subTest(view=view_xmlid):
                arch = self._get_variant_form_arch(
                    self.user_with_group, view_xmlid
                )

                self.assertIn('name="action_generate_ean13"', arch)

    def test_button_hidden_in_variant_forms_for_user_without_group(self):
        for view_xmlid in VARIANT_FORM_VIEWS:
            with self.subTest(view=view_xmlid):
                arch = self._get_variant_form_arch(
                    self.user_without_group, view_xmlid
                )

                self.assertNotIn('name="action_generate_ean13"', arch)
