import csv
import io


def generate_fuel_invoice_csv(data):
    return _single_row_csv(
        [
            "Invoice Date",
            "Invoice Number",
            "Vendor",
            "Gallons",
            "Amount",
            "Received Gallons",
            "Expected Amount",
        ],
        [
            data.get("invoice_date", ""),
            data.get("invoice_number", ""),
            data.get("vendor", ""),
            data.get("gallons", ""),
            data.get("amount", ""),
            data.get("received_gallons", ""),
            data.get("expected_amount", ""),
        ],
    )


def generate_expense_invoice_csv(data):
    return _single_row_csv(
        ["Bill ID", "Vendor", "Bill Date", "Amount", "Payment Method", "External Ref"],
        [
            data.get("bill_id", ""),
            data.get("vendor", ""),
            data.get("bill_date", ""),
            data.get("amount", ""),
            data.get("payment_method", ""),
            data.get("external_ref", ""),
        ],
    )


def generate_lottery_settlement_csv(data):
    return _single_row_csv(
        ["Settlement Date", "Settlement ID", "Net Due", "Retailer Commission"],
        [
            data.get("settlement_date", ""),
            data.get("settlement_id", ""),
            data.get("net_due", ""),
            data.get("retailer_commission", ""),
        ],
    )


def _single_row_csv(headers, values):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(headers)
    writer.writerow(values)
    return output.getvalue()

