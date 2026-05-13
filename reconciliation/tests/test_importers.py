import unittest

from reconciliation.importers import (
    parse_card_bank_report,
    parse_expense_report,
    parse_fuel_invoice_report,
    parse_lottery_settlement_report,
    parse_pos_daily_report,
    parse_woocommerce_orders,
)


class ImporterTests(unittest.TestCase):
    def test_pos_daily_report_creates_tender_transactions(self):
        content = (
            "Business Date,Close ID,Cash Sales,Card Sales,Fuel Sales,Lottery Net,Suspended Sales\n"
            "2026-05-01,close-1001,421.55,1290.10,3200.00,88.25,0.00\n"
        )

        transactions = parse_pos_daily_report(content, source_import_id="import-pos")

        self.assertEqual(len(transactions), 4)
        self.assertEqual(
            {(txn.category, txn.tender_type, txn.amount) for txn in transactions},
            {
                ("sale", "cash", "421.55"),
                ("sale", "card", "1290.10"),
                ("sale", "fuel", "3200.00"),
                ("settlement", "lottery", "88.25"),
            },
        )

    def test_pos_daily_report_accepts_tab_delimited_pasted_text(self):
        content = (
            "Business Date\tClose ID\tCash Sales\tCard Sales\tFuel Sales\tLottery Net\tSuspended Sales\n"
            "2026-05-01\tclose-1001\t421.55\t1290.10\t3200.00\t88.25\t0.00\n"
        )

        transactions = parse_pos_daily_report(content, source_import_id="import-pos")

        self.assertEqual(len(transactions), 4)
        self.assertEqual(transactions[0].external_ref, "close-1001")

    def test_card_bank_report_creates_deposit_transaction(self):
        content = (
            "Posted Date,Deposit Ref,Description,Amount\n"
            "2026-05-02,batch-9001,CARD SETTLEMENT CLOSE 1001,1280.10\n"
        )

        transactions = parse_card_bank_report(content, source_import_id="import-bank")

        self.assertEqual(len(transactions), 1)
        self.assertEqual(transactions[0].category, "deposit")
        self.assertEqual(transactions[0].tender_type, "card")
        self.assertEqual(transactions[0].amount, "1280.10")

    def test_woocommerce_completed_orders_create_online_sales(self):
        content = (
            "Order ID,Date,Status,Total,Payment Method\n"
            "7781,2026-05-01,completed,64.25,card\n"
            "7782,2026-05-01,pending,19.99,card\n"
        )

        transactions = parse_woocommerce_orders(content, source_import_id="import-woo")

        self.assertEqual(len(transactions), 1)
        self.assertEqual(transactions[0].external_ref, "7781")
        self.assertEqual(transactions[0].tender_type, "online")

    def test_fuel_invoice_report_creates_invoice_transaction(self):
        content = (
            "Invoice Date,Invoice Number,Vendor,Gallons,Amount\n"
            "2026-05-01,FUEL-7001,Shell Oil Co. #123,1200.000,3198.75\n"
        )

        transactions = parse_fuel_invoice_report(content, source_import_id="import-fuel")

        self.assertEqual(len(transactions), 1)
        self.assertEqual(transactions[0].category, "invoice")
        self.assertEqual(transactions[0].tender_type, "fuel")
        self.assertEqual(transactions[0].payee_key, "shell-oil-123")

    def test_fuel_invoice_report_picks_up_optional_variance_columns(self):
        content = (
            "Invoice Date,Invoice Number,Vendor,Gallons,Amount,Received Gallons,Expected Amount\n"
            "2026-05-01,FUEL-7001,Shell Oil Co. #123,1200.000,3198.75,1188.500,\n"
            "2026-05-02,FUEL-7002,Shell Oil Co. #123,1100.000,2937.00,,2900.00\n"
        )

        transactions = parse_fuel_invoice_report(content, source_import_id="import-fuel")

        self.assertEqual(transactions[0].metadata["received_gallons"], "1188.500")
        self.assertNotIn("expected_amount", transactions[0].metadata)
        self.assertEqual(transactions[1].metadata["expected_amount"], "2900.00")
        self.assertNotIn("received_gallons", transactions[1].metadata)

    def test_lottery_settlement_report_creates_settlement_transaction(self):
        content = (
            "Settlement Date,Settlement ID,Net Due,Retailer Commission\n"
            "2026-05-01,LOT-4401,90.25,12.00\n"
        )

        transactions = parse_lottery_settlement_report(content, source_import_id="import-lottery")

        self.assertEqual(len(transactions), 1)
        self.assertEqual(transactions[0].category, "settlement")
        self.assertEqual(transactions[0].tender_type, "lottery")
        self.assertEqual(transactions[0].amount, "90.25")


    def test_expense_report_creates_expense_transactions(self):
        content = (
            "Bill ID,Vendor,Bill Date,Amount,Payment Method,External Ref\n"
            "BILL-100,Shell Oil Co. #123,2026-05-01,42.10,ACH,EXT-77\n"
            "BILL-101,Acme Supplies LLC,2026-05-02,128.00,Credit,\n"
        )

        transactions = parse_expense_report(content, source_import_id="import-exp")

        self.assertEqual(len(transactions), 2)
        self.assertEqual(transactions[0].category, "expense")
        self.assertEqual(transactions[0].tender_type, "bank")
        self.assertEqual(transactions[0].external_ref, "EXT-77")
        self.assertEqual(transactions[0].payee_key, "shell-oil-123")
        self.assertEqual(transactions[1].tender_type, "card")
        self.assertEqual(transactions[1].payee_key, "acme-supplies")
        self.assertEqual(transactions[1].external_ref, "BILL-101")

    def test_expense_report_skips_blank_rows(self):
        content = (
            "Bill ID,Vendor,Bill Date,Amount,Payment Method\n"
            ",,,,\n"
            "BILL-200,Vendor X,2026-05-03,10.00,Cash\n"
        )

        transactions = parse_expense_report(content, source_import_id="import-exp")

        self.assertEqual(len(transactions), 1)
        self.assertEqual(transactions[0].tender_type, "cash")


if __name__ == "__main__":
    unittest.main()
