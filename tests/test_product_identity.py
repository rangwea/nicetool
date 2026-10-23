from unittest import TestCase

from core.settings import Settings


class ProductIdentityTest(TestCase):
    def test_runtime_defaults_use_nicetool_identity(self):
        defaults = {
            name: Settings.model_fields[name].default
            for name in (
                "storage_secret",
                "mysql_database",
                "auth_cookie_name",
                "auth_flow_cookie_name",
                "auth_jwt_issuer",
                "auth_jwt_audience",
            )
        }

        self.assertEqual(defaults["mysql_database"], "nicetool")
        self.assertEqual(defaults["auth_cookie_name"], "nicetool_session")
        self.assertEqual(defaults["auth_flow_cookie_name"], "nicetool_auth_flow")
        self.assertEqual(defaults["auth_jwt_issuer"], "nicetool")
        self.assertEqual(defaults["auth_jwt_audience"], "nicetool-web")
        self.assertTrue(defaults["storage_secret"].startswith("nicetool-"))
