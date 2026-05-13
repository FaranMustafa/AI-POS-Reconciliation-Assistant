import unittest

from reconciliation.engine import run_reconciliation
from reconciliation.types import CanonicalTransaction


def txn(
    txn_id,
    source_type,
    business_date,
    category,
    tender_type,
    amount,
    external_ref=None,
    payee_key=None,
    description="",
    metadata=None,
):
    return CanonicalTransaction(
        id=txn_id,
        source_import_id="import-1",
        source_type=source_type,
        business_date=business_date,
        posted_at=f"{business_date}T12:00:00Z",
        category=category,
        tender_type=tender_type,
        external_ref=external_ref,
        payee_key=payee_key,
        description=description or txn_id,
        amount=amount,
        metadata=metadata or {},
    )


class ReconciliationEngineTests(unittest.TestCase):
    def test_flags_card_settlement_short_payment(self):
        issues = run_reconciliation(
            run_id="run-1",
            transactions=[
                txn("pos-card", "pos_daily", "2026-05-01", "sale", "card", "1290.10"),
                txn("bank-card", "card_bank", "2026-05-01", "deposit", "card", "1280.10"),
            ],
        )

        self.assertEqual(issues[0].category, "settlement_gap")
        self.assertIn("short by 10.00", issues[0].evidence[0])

    def test_flags_duplicate_payee_entries(self):
        issues = run_reconciliation(
            run_id="run-1",
            transactions=[
                txn("expense-1", "expense", "2026-05-01", "expense", "bank", "42.10", payee_key="shell-oil-123"),
                txn("expense-2", "expense", "2026-05-01", "expense", "bank", "42.10", payee_key="shell-oil-123"),
            ],
        )

        self.assertEqual(issues[0].category, "duplicate_entry")
        self.assertEqual(set(issues[0].related_transaction_ids), {"expense-1", "expense-2"})

    def test_flags_unresolved_suspended_sales(self):
        issues = run_reconciliation(
            run_id="run-1",
            transactions=[
                txn("suspended", "pos_daily", "2026-05-01", "adjustment", "unknown", "15.00", description="Suspended sales"),
            ],
        )

        self.assertEqual(issues[0].category, "unresolved_suspended_sale")

    def test_flags_lottery_settlement_mismatch(self):
        issues = run_reconciliation(
            run_id="run-1",
            transactions=[
                txn("pos-lottery", "pos_daily", "2026-05-01", "settlement", "lottery", "88.25"),
                txn("lottery-settlement", "lottery_settlement", "2026-05-01", "settlement", "lottery", "90.25"),
            ],
        )

        self.assertEqual(issues[0].category, "total_mismatch")
        self.assertIn("differs by 2.00", issues[0].evidence[0])


    def test_flags_missing_deposit_for_pos_card_sales(self):
        issues = run_reconciliation(
            run_id="run-1",
            transactions=[
                txn("pos-card", "pos_daily", "2026-05-01", "sale", "card", "1290.10"),
            ],
        )

        missing = [issue for issue in issues if issue.category == "missing_entry"]
        self.assertTrue(missing)
        self.assertIn("no matching deposit", missing[0].title)

    def test_flags_orphan_card_deposit(self):
        issues = run_reconciliation(
            run_id="run-1",
            transactions=[
                txn("bank-card", "card_bank", "2026-05-03", "deposit", "card", "500.00"),
            ],
        )

        orphan = [issue for issue in issues if "no matching POS close" in issue.title]
        self.assertEqual(len(orphan), 1)

    def test_flags_woocommerce_orders_not_in_pos(self):
        issues = run_reconciliation(
            run_id="run-1",
            transactions=[
                txn("woo-1", "woocommerce", "2026-05-01", "sale", "online", "64.25", external_ref="7781"),
            ],
        )

        missing = [issue for issue in issues if issue.category == "missing_entry"]
        self.assertTrue(missing)
        self.assertIn("WooCommerce", missing[0].title)

    def test_flags_woocommerce_vs_pos_online_mismatch(self):
        issues = run_reconciliation(
            run_id="run-1",
            transactions=[
                txn("woo-1", "woocommerce", "2026-05-01", "sale", "online", "120.00", external_ref="7781"),
                txn("pos-online", "pos_daily", "2026-05-01", "sale", "online", "100.00"),
                # Pair the POS online sale with a deposit so we don't get a missing-deposit issue.
            ],
        )

        mismatch = [issue for issue in issues if issue.category == "total_mismatch" and "WooCommerce" in issue.title]
        self.assertEqual(len(mismatch), 1)
        self.assertIn("differs by 20.00", mismatch[0].evidence[0])

    def test_flags_fuel_invoice_gallons_variance(self):
        issues = run_reconciliation(
            run_id="run-1",
            transactions=[
                txn(
                    "fuel-1",
                    "fuel_invoice",
                    "2026-05-01",
                    "invoice",
                    "fuel",
                    "3198.75",
                    external_ref="FUEL-7001",
                    payee_key="shell-oil-123",
                    metadata={"gallons": "1200.000", "received_gallons": "1188.500"},
                ),
            ],
        )

        variance = [issue for issue in issues if "gallons" in issue.title.lower()]
        self.assertEqual(len(variance), 1)
        self.assertIn("off by 11.500", variance[0].evidence[0])

    def test_flags_fuel_invoice_amount_variance(self):
        issues = run_reconciliation(
            run_id="run-1",
            transactions=[
                txn(
                    "fuel-1",
                    "fuel_invoice",
                    "2026-05-01",
                    "invoice",
                    "fuel",
                    "3198.75",
                    external_ref="FUEL-7001",
                    payee_key="shell-oil-123",
                    metadata={"expected_amount": "3150.00"},
                ),
            ],
        )

        variance = [issue for issue in issues if issue.category == "suspicious_total"]
        self.assertEqual(len(variance), 1)
        self.assertIn("off by 48.75", variance[0].evidence[0])

    def test_flags_cross_source_expense_duplicates(self):
        issues = run_reconciliation(
            run_id="run-1",
            transactions=[
                txn(
                    "bill-1",
                    "expense",
                    "2026-05-01",
                    "expense",
                    "bank",
                    "120.00",
                    payee_key="acme-supplies",
                    external_ref="BILL-100",
                ),
                txn(
                    "bank-1",
                    "card_bank",
                    "2026-05-01",
                    "deposit",
                    "card",
                    "120.00",
                    payee_key="acme-supplies",
                    external_ref="DEP-99",
                ),
            ],
        )

        cross = [
            issue
            for issue in issues
            if issue.category == "duplicate_entry"
            and "across multiple sources" in issue.title
        ]
        self.assertEqual(len(cross), 1)


if __name__ == "__main__":
    unittest.main()

