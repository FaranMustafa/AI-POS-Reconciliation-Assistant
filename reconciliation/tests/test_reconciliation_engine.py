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
        metadata={},
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


if __name__ == "__main__":
    unittest.main()

