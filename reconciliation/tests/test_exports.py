import csv
import io
import unittest

from reconciliation.exports import issues_to_csv
from reconciliation.types import ReconciliationIssue


class IssueExportTests(unittest.TestCase):
    def test_issues_to_csv_writes_expected_headers_and_rows(self):
        content = issues_to_csv(
            [
                ReconciliationIssue(
                    id="issue-1",
                    run_id="run-1",
                    severity="high",
                    category="settlement_gap",
                    title="Card settlement, short",
                    evidence=[
                        "POS card sales 1290.10",
                        "Deposits 1280.10\nshort by 10.00",
                    ],
                    recommended_action='Check "processor" batch timing.',
                    related_transaction_ids=["pos-card", "bank-card"],
                )
            ]
        )

        rows = list(csv.reader(io.StringIO(content)))

        self.assertEqual(
            rows[0],
            [
                "Severity",
                "Category",
                "Title",
                "Evidence",
                "Recommended Action",
                "Related Transactions",
            ],
        )
        self.assertEqual(rows[1][0], "high")
        self.assertEqual(rows[1][1], "settlement_gap")
        self.assertEqual(rows[1][2], "Card settlement, short")
        self.assertEqual(rows[1][3], "POS card sales 1290.10 | Deposits 1280.10\nshort by 10.00")
        self.assertEqual(rows[1][4], 'Check "processor" batch timing.')
        self.assertEqual(rows[1][5], "pos-card | bank-card")

    def test_issues_to_csv_includes_headers_when_empty(self):
        content = issues_to_csv([])

        rows = list(csv.reader(io.StringIO(content)))

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][0], "Severity")


if __name__ == "__main__":
    unittest.main()

