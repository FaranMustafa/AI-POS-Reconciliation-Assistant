import csv
from decimal import Decimal, ROUND_HALF_UP
from io import StringIO
from typing import Dict, Iterable, List

from reconciliation.normalization import normalize_payee
from reconciliation.types import CanonicalTransaction


def _rows(content: str) -> Iterable[Dict[str, str]]:
    reader = csv.DictReader(StringIO(content))
    for row in reader:
        if any((value or "").strip() for value in row.values()):
            yield {key.strip(): (value or "").strip() for key, value in row.items()}


def _money(value: str) -> str:
    normalized = (value or "0").replace(",", "").replace("$", "").strip()
    return str(Decimal(normalized).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _txn(
    *,
    transaction_id: str,
    source_import_id: str,
    source_type: str,
    business_date: str,
    category: str,
    tender_type: str,
    amount: str,
    external_ref: str = None,
    payee_key: str = None,
    description: str,
    metadata=None,
) -> CanonicalTransaction:
    return CanonicalTransaction(
        id=transaction_id,
        source_import_id=source_import_id,
        source_type=source_type,
        business_date=business_date,
        posted_at=f"{business_date}T12:00:00Z",
        category=category,
        tender_type=tender_type,
        external_ref=external_ref,
        payee_key=payee_key,
        description=description,
        amount=_money(amount),
        metadata=metadata or {},
    )


def parse_pos_daily_report(content: str, source_import_id: str) -> List[CanonicalTransaction]:
    transactions: List[CanonicalTransaction] = []
    for row in _rows(content):
        business_date = row["Business Date"]
        close_id = row["Close ID"]
        tender_fields = [
            ("cash", "Cash Sales", "sale"),
            ("card", "Card Sales", "sale"),
            ("fuel", "Fuel Sales", "sale"),
            ("lottery", "Lottery Net", "settlement"),
        ]
        for tender_type, field_name, category in tender_fields:
            amount = _money(row.get(field_name, "0"))
            if Decimal(amount) != Decimal("0.00"):
                transactions.append(
                    _txn(
                        transaction_id=f"{source_import_id}:{close_id}:{tender_type}",
                        source_import_id=source_import_id,
                        source_type="pos_daily",
                        business_date=business_date,
                        category=category,
                        tender_type=tender_type,
                        amount=amount,
                        external_ref=close_id,
                        description=f"POS {field_name}",
                    )
                )
        suspended = _money(row.get("Suspended Sales", "0"))
        if Decimal(suspended) != Decimal("0.00"):
            transactions.append(
                _txn(
                    transaction_id=f"{source_import_id}:{close_id}:suspended",
                    source_import_id=source_import_id,
                    source_type="pos_daily",
                    business_date=business_date,
                    category="adjustment",
                    tender_type="unknown",
                    amount=suspended,
                    external_ref=close_id,
                    description="Suspended sales",
                )
            )
    return transactions


def parse_card_bank_report(content: str, source_import_id: str) -> List[CanonicalTransaction]:
    return [
        _txn(
            transaction_id=f"{source_import_id}:{row['Deposit Ref']}",
            source_import_id=source_import_id,
            source_type="card_bank",
            business_date=row["Posted Date"],
            category="deposit",
            tender_type="card",
            amount=row["Amount"],
            external_ref=row["Deposit Ref"],
            description=row["Description"],
        )
        for row in _rows(content)
    ]


def parse_woocommerce_orders(content: str, source_import_id: str) -> List[CanonicalTransaction]:
    transactions: List[CanonicalTransaction] = []
    for row in _rows(content):
        if row["Status"].lower() != "completed":
            continue
        order_id = row["Order ID"]
        transactions.append(
            _txn(
                transaction_id=f"{source_import_id}:woo:{order_id}",
                source_import_id=source_import_id,
                source_type="woocommerce",
                business_date=row["Date"],
                category="sale",
                tender_type="online",
                amount=row["Total"],
                external_ref=order_id,
                description=f"WooCommerce order {order_id}",
                metadata={"payment_method": row["Payment Method"]},
            )
        )
    return transactions


def parse_fuel_invoice_report(content: str, source_import_id: str) -> List[CanonicalTransaction]:
    transactions: List[CanonicalTransaction] = []
    for row in _rows(content):
        invoice_number = row["Invoice Number"]
        vendor = row["Vendor"]
        metadata = {"vendor": vendor, "gallons": row["Gallons"]}
        received_gallons = (row.get("Received Gallons", "") or "").strip()
        if received_gallons:
            metadata["received_gallons"] = received_gallons
        expected_amount = (row.get("Expected Amount", "") or "").strip()
        if expected_amount:
            metadata["expected_amount"] = expected_amount
        transactions.append(
            _txn(
                transaction_id=f"{source_import_id}:fuel:{invoice_number}",
                source_import_id=source_import_id,
                source_type="fuel_invoice",
                business_date=row["Invoice Date"],
                category="invoice",
                tender_type="fuel",
                amount=row["Amount"],
                external_ref=invoice_number,
                payee_key=normalize_payee(vendor),
                description=f"Fuel invoice {invoice_number}",
                metadata=metadata,
            )
        )
    return transactions


_TENDER_BY_PAYMENT_METHOD = {
    "cash": "cash",
    "card": "card",
    "credit": "card",
    "credit card": "card",
    "debit": "card",
    "ach": "bank",
    "bank": "bank",
    "wire": "bank",
    "check": "bank",
    "online": "online",
}


def parse_expense_report(content: str, source_import_id: str) -> List[CanonicalTransaction]:
    """Parse a bookkeeping export of payee/expense bills.

    Expected columns: ``Bill ID``, ``Vendor``, ``Bill Date``, ``Amount``,
    ``Payment Method`` (optional), ``External Ref`` (optional).
    """

    transactions: List[CanonicalTransaction] = []
    for row in _rows(content):
        bill_id = row.get("Bill ID") or row.get("Reference") or row.get("ID") or ""
        vendor = row.get("Vendor") or row.get("Payee") or ""
        if not vendor and not bill_id:
            continue
        payment_method = (row.get("Payment Method", "") or "").strip().lower()
        tender_type = _TENDER_BY_PAYMENT_METHOD.get(payment_method, "unknown")
        external_ref = row.get("External Ref") or bill_id or None
        bill_date = row.get("Bill Date") or row.get("Date") or ""
        transactions.append(
            _txn(
                transaction_id=f"{source_import_id}:expense:{bill_id or external_ref or vendor}",
                source_import_id=source_import_id,
                source_type="expense",
                business_date=bill_date,
                category="expense",
                tender_type=tender_type,
                amount=row.get("Amount", "0"),
                external_ref=external_ref or None,
                payee_key=normalize_payee(vendor) if vendor else None,
                description=f"Bill {bill_id or external_ref or vendor}".strip(),
                metadata={"vendor": vendor, "payment_method": payment_method},
            )
        )
    return transactions


def parse_lottery_settlement_report(content: str, source_import_id: str) -> List[CanonicalTransaction]:
    transactions: List[CanonicalTransaction] = []
    for row in _rows(content):
        settlement_id = row["Settlement ID"]
        transactions.append(
            _txn(
                transaction_id=f"{source_import_id}:lottery:{settlement_id}",
                source_import_id=source_import_id,
                source_type="lottery_settlement",
                business_date=row["Settlement Date"],
                category="settlement",
                tender_type="lottery",
                amount=row["Net Due"],
                external_ref=settlement_id,
                description=f"Lottery settlement {settlement_id}",
                metadata={"retailer_commission": row["Retailer Commission"]},
            )
        )
    return transactions

