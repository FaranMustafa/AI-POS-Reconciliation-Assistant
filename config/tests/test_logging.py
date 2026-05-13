from django.test import SimpleTestCase

from config.logging import build_log_extra


class LoggingHelperTests(SimpleTestCase):
    def test_build_log_extra_keeps_event_name_and_context(self):
        extra = build_log_extra(
            "import_processed",
            tenant_id=7,
            run_id=9,
            import_file_id=11,
            transaction_count=4,
        )

        self.assertEqual(
            extra,
            {
                "event": "import_processed",
                "tenant_id": 7,
                "run_id": 9,
                "import_file_id": 11,
                "transaction_count": 4,
            },
        )
