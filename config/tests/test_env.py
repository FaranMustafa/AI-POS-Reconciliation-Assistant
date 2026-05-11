from django.test import SimpleTestCase

from config.env import build_database_config, parse_allowed_hosts


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

