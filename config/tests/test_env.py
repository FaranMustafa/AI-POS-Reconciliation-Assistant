from django.test import SimpleTestCase

from config.env import build_database_config, build_security_config, parse_allowed_hosts


class EnvironmentConfigTests(SimpleTestCase):
    def test_parse_allowed_hosts_trims_empty_values(self):
        self.assertEqual(
            parse_allowed_hosts("localhost, 127.0.0.1, app.example.com, "),
            ["localhost", "127.0.0.1", "app.example.com"],
        )

    def test_build_database_config_defaults_to_sqlite(self):
        config = build_database_config("", "/app")

        self.assertEqual(config["ENGINE"], "django.db.backends.sqlite3")
        self.assertEqual(str(config["NAME"]), "/app/db.sqlite3")

    def test_build_database_config_parses_postgres_url(self):
        config = build_database_config(
            "postgresql://recon:secret@db.example.com:5432/pos_reconciliation",
            "/app",
        )

        self.assertEqual(config["ENGINE"], "django.db.backends.postgresql")
        self.assertEqual(config["NAME"], "pos_reconciliation")
        self.assertEqual(config["USER"], "recon")
        self.assertEqual(config["PASSWORD"], "secret")
        self.assertEqual(config["HOST"], "db.example.com")
        self.assertEqual(config["PORT"], "5432")

    def test_build_security_config_hardens_when_debug_is_false(self):
        config = build_security_config(debug=False)

        self.assertTrue(config["SESSION_COOKIE_SECURE"])
        self.assertTrue(config["CSRF_COOKIE_SECURE"])
        self.assertEqual(config["SECURE_PROXY_SSL_HEADER"], ("HTTP_X_FORWARDED_PROTO", "https"))
        self.assertEqual(config["SECURE_HSTS_SECONDS"], 31536000)

    def test_build_security_config_remains_dev_friendly_when_debug_is_true(self):
        config = build_security_config(debug=True)

        self.assertFalse(config["SESSION_COOKIE_SECURE"])
        self.assertFalse(config["CSRF_COOKIE_SECURE"])
        self.assertEqual(config["SECURE_HSTS_SECONDS"], 0)
