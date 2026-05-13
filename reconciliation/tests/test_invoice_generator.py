import csv
import io
import unittest

from reconciliation.importers import (
    parse_expense_report,
    parse_fuel_invoice_report,
    parse_lottery_settlement_report,
)
from reconciliation.invoice_generator import (
    generate_expense_invoice_csv,
    generate_fuel_invoice_csv,
    generate_lottery_settlement_csv,
)


class InvoiceGeneratorTests(unittest.TestCase):
    def test_generate_fuel_invoice_csv_is_parseable_by_engine(self):
        content = generate_fuel_invoice_csv(
            {
                "invoice_date": "2026-05-01",
                "invoice_number": "FUEL-9001",
                "vendor": "Shell Oil Co. #123",
                "gallons": "1200.000",
                "amount": "3198.75",
                "received_gallons": "1188.500",
                "expected_amount": "3150.00",
            }
        )

        rows = list(csv.reader(io.StringIO(content)))
        self.assertEqual(
            rows[0],
            [
                "Invoice Date",
                "Invoice Number",
                "Vendor",
                "Gallons",
                "Amount",
                "Received Gallons",
                "Expected Amount",
            ],
        )
        transactions = parse_fuel_invoice_report(content, "generated-fuel")
        self.assertEqual(len(transactions), 1)
        self.assertEqual(transactions[0].external_ref, "FUEL-9001")
        self.assertEqual(transactions[0].metadata["received_gallons"], "1188.500")

    def test_generate_expense_invoice_csv_is_parseable_by_engine(self):
        content = generate_expense_invoice_csv(
            {
                "bill_id": "BILL-9001",
                "vendor": "Acme Supplies LLC",
                "bill_date": "2026-05-02",
                "amount": "128.00",
                "payment_method": "Credit",
                "external_ref": "EXT-9001",
            }
        )

        transactions = parse_expense_report(content, "generated-expense")
        self.assertEqual(len(transactions), 1)
        self.assertEqual(transactions[0].category, "expense")
        self.assertEqual(transactions[0].payee_key, "acme-supplies")
        self.assertEqual(transactions[0].external_ref, "EXT-9001")

    def test_generate_lottery_settlement_csv_is_parseable_by_engine(self):
        content = generate_lottery_settlement_csv(
            {
                "settlement_date": "2026-05-03",
                "settlement_id": "LOT-9001",
                "net_due": "90.25",
                "retailer_commission": "12.00",
            }
        )

        transactions = parse_lottery_settlement_report(content, "generated-lottery")
        self.assertEqual(len(transactions), 1)
        self.assertEqual(transactions[0].category, "settlement")
        self.assertEqual(transactions[0].amount, "90.25")


if __name__ == "__main__":
    unittest.main()

