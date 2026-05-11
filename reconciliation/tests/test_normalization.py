import unittest

from reconciliation.normalization import create_duplicate_key, normalize_payee


class NormalizationTests(unittest.TestCase):
    def test_normalize_payee_collapses_common_vendor_variants(self):
        self.assertEqual(normalize_payee("  Shell Oil Co. #123 "), "shell-oil-123")
        self.assertEqual(normalize_payee("SHELL OIL COMPANY 123"), "shell-oil-123")

    def test_duplicate_key_prefers_external_reference_when_present(self):
        key = create_duplicate_key(
            business_date="2026-05-01",
            amount="42.10",
            payee_key="shell-oil-123",
            external_ref="INV-100",
        )

        self.assertEqual(key, "ref|INV-100")

    def test_duplicate_key_uses_date_amount_and_payee_without_reference(self):
        key = create_duplicate_key(
            business_date="2026-05-01",
            amount="42.10",
            payee_key="shell-oil-123",
            external_ref=None,
        )

        self.assertEqual(key, "2026-05-01|42.10|shell-oil-123")


if __name__ == "__main__":
    unittest.main()

