from collections import defaultdict
from decimal import Decimal
from typing import Dict, Iterable, List

from reconciliation.normalization import create_duplicate_key
from reconciliation.types import CanonicalTransaction, ReconciliationIssue


SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}


def run_reconciliation(run_id: str, transactions: List[CanonicalTransaction]) -> List[ReconciliationIssue]:
    issues: List[ReconciliationIssue] = []
    issues.extend(_detect_card_settlement_gaps(run_id, transactions))
    issues.extend(_detect_missing_settlements(run_id, transactions))
    issues.extend(_detect_duplicate_entries(run_id, transactions))
    issues.extend(_detect_suspended_sales(run_id, transactions))
    issues.extend(_detect_lottery_settlement_mismatches(run_id, transactions))
    issues.extend(_detect_woocommerce_pos_gap(run_id, transactions))
    issues.extend(_detect_fuel_invoice_variances(run_id, transactions))
    return sorted(issues, key=lambda issue: (SEVERITY_ORDER[issue.severity], issue.category, issue.title))


def _sum_amount(transactions: Iterable[CanonicalTransaction]) -> Decimal:
    return sum((Decimal(txn.amount) for txn in transactions), Decimal("0.00"))


def _group_by_date(transactions: Iterable[CanonicalTransaction]) -> Dict[str, List[CanonicalTransaction]]:
    grouped: Dict[str, List[CanonicalTransaction]] = defaultdict(list)
    for transaction in transactions:
        grouped[transaction.business_date].append(transaction)
    return grouped


def _detect_card_settlement_gaps(
    run_id: str, transactions: List[CanonicalTransaction]
) -> List[ReconciliationIssue]:
    pos_card = _group_by_date(
        txn for txn in transactions if txn.source_type == "pos_daily" and txn.category == "sale" and txn.tender_type == "card"
    )
    bank_card = _group_by_date(
        txn for txn in transactions if txn.source_type == "card_bank" and txn.category == "deposit" and txn.tender_type == "card"
    )
    issues: List[ReconciliationIssue] = []
    for business_date, pos_transactions in pos_card.items():
        pos_total = _sum_amount(pos_transactions)
        bank_transactions = bank_card.get(business_date, [])
        bank_total = _sum_amount(bank_transactions)
        if pos_total != bank_total:
            difference = abs(pos_total - bank_total)
            direction = "short by" if bank_total < pos_total else "over by"
            issues.append(
                ReconciliationIssue(
                    id=f"{run_id}:card-settlement:{business_date}",
                    run_id=run_id,
                    severity="high",
                    category="settlement_gap",
                    title=f"Card settlement does not match POS sales for {business_date}",
                    evidence=[
                        f"POS card sales {pos_total:.2f}; bank/card deposits {bank_total:.2f}; {direction} {difference:.2f}."
                    ],
                    recommended_action="Check processor batch timing, fees, chargebacks, and missing deposits.",
                    related_transaction_ids=[txn.id for txn in pos_transactions + bank_transactions],
                )
            )
    return issues


_DUPLICATE_CATEGORIES = {"expense", "invoice"}
_CROSS_SOURCE_PAYABLE_CATEGORIES = {"expense", "invoice", "deposit"}


def _detect_duplicate_entries(
    run_id: str, transactions: List[CanonicalTransaction]
) -> List[ReconciliationIssue]:
    buckets: Dict[str, List[CanonicalTransaction]] = defaultdict(list)
    for transaction in transactions:
        if transaction.category not in _DUPLICATE_CATEGORIES:
            continue
        key = create_duplicate_key(
            business_date=transaction.business_date,
            amount=transaction.amount,
            payee_key=transaction.payee_key,
            external_ref=transaction.external_ref,
        )
        buckets[key].append(transaction)

    issues: List[ReconciliationIssue] = []
    for key, matches in buckets.items():
        if len(matches) < 2:
            continue
        issues.append(
            ReconciliationIssue(
                id=f"{run_id}:duplicate:{key}",
                run_id=run_id,
                severity="medium",
                category="duplicate_entry",
                title="Possible duplicate payee or invoice entry",
                evidence=[f"{len(matches)} entries share duplicate key {key}."],
                recommended_action="Review the related entries and void or merge the duplicate record.",
                related_transaction_ids=[txn.id for txn in matches],
            )
        )

    cross_source_buckets: Dict[str, List[CanonicalTransaction]] = defaultdict(list)
    for transaction in transactions:
        if transaction.category not in _CROSS_SOURCE_PAYABLE_CATEGORIES:
            continue
        if not transaction.payee_key:
            continue
        cross_key = (
            f"{transaction.business_date}|{transaction.amount}|{transaction.payee_key}"
        )
        cross_source_buckets[cross_key].append(transaction)

    for key, matches in cross_source_buckets.items():
        sources = {txn.source_type for txn in matches}
        if len(matches) < 2 or len(sources) < 2:
            continue
        issues.append(
            ReconciliationIssue(
                id=f"{run_id}:duplicate-cross:{key}",
                run_id=run_id,
                severity="medium",
                category="duplicate_entry",
                title="Expense appears across multiple sources",
                evidence=[
                    f"{len(matches)} entries with payee {matches[0].payee_key} on {matches[0].business_date}"
                    f" for {matches[0].amount} across {sorted(sources)}."
                ],
                recommended_action="Confirm the expense was not posted twice (e.g., POS payout, bill, bank/card).",
                related_transaction_ids=[txn.id for txn in matches],
            )
        )
    return issues


def _detect_suspended_sales(
    run_id: str, transactions: List[CanonicalTransaction]
) -> List[ReconciliationIssue]:
    issues: List[ReconciliationIssue] = []
    for transaction in transactions:
        if transaction.category == "adjustment" and "suspended" in transaction.description.lower():
            issues.append(
                ReconciliationIssue(
                    id=f"{run_id}:suspended:{transaction.id}",
                    run_id=run_id,
                    severity="medium",
                    category="unresolved_suspended_sale",
                    title="Suspended sale remains unresolved after close",
                    evidence=[f"{transaction.business_date} has suspended sales of {transaction.amount}."],
                    recommended_action="Resolve the suspended transaction or document why it should remain open.",
                    related_transaction_ids=[transaction.id],
                )
            )
    return issues


def _detect_missing_settlements(
    run_id: str, transactions: List[CanonicalTransaction]
) -> List[ReconciliationIssue]:
    pos_card_dates = {
        txn.business_date
        for txn in transactions
        if txn.source_type == "pos_daily"
        and txn.category == "sale"
        and txn.tender_type == "card"
    }
    bank_card_by_date: Dict[str, List[CanonicalTransaction]] = defaultdict(list)
    for txn in transactions:
        if txn.source_type == "card_bank" and txn.category == "deposit" and txn.tender_type == "card":
            bank_card_by_date[txn.business_date].append(txn)

    issues: List[ReconciliationIssue] = []
    for business_date in sorted(pos_card_dates):
        if business_date in bank_card_by_date:
            continue
        related = [
            txn.id
            for txn in transactions
            if txn.business_date == business_date
            and txn.source_type == "pos_daily"
            and txn.tender_type == "card"
        ]
        issues.append(
            ReconciliationIssue(
                id=f"{run_id}:missing-deposit:{business_date}",
                run_id=run_id,
                severity="high",
                category="missing_entry",
                title=f"POS card sales have no matching deposit for {business_date}",
                evidence=[
                    f"POS reported card sales for {business_date} but no card/bank deposit was imported on that date."
                ],
                recommended_action="Confirm the processor batched the deposit and that the bank file is current.",
                related_transaction_ids=related,
            )
        )

    for business_date, deposits in bank_card_by_date.items():
        if business_date in pos_card_dates:
            continue
        issues.append(
            ReconciliationIssue(
                id=f"{run_id}:orphan-deposit:{business_date}",
                run_id=run_id,
                severity="medium",
                category="missing_entry",
                title=f"Card deposit on {business_date} has no matching POS close",
                evidence=[
                    f"{len(deposits)} card deposit(s) on {business_date} without a POS daily close for the same date."
                ],
                recommended_action="Check whether the POS close was uploaded or whether the deposit belongs to another business date.",
                related_transaction_ids=[txn.id for txn in deposits],
            )
        )
    return issues


def _detect_woocommerce_pos_gap(
    run_id: str, transactions: List[CanonicalTransaction]
) -> List[ReconciliationIssue]:
    woo_by_date = _group_by_date(
        txn for txn in transactions if txn.source_type == "woocommerce" and txn.category == "sale"
    )
    pos_online_by_date = _group_by_date(
        txn
        for txn in transactions
        if txn.source_type == "pos_daily"
        and txn.category == "sale"
        and txn.tender_type == "online"
    )

    issues: List[ReconciliationIssue] = []
    all_dates = set(woo_by_date) | set(pos_online_by_date)
    for business_date in sorted(all_dates):
        woo_transactions = woo_by_date.get(business_date, [])
        pos_transactions = pos_online_by_date.get(business_date, [])
        woo_total = _sum_amount(woo_transactions)
        pos_total = _sum_amount(pos_transactions)
        if woo_total == pos_total:
            continue
        difference = abs(woo_total - pos_total)
        if woo_total > Decimal("0.00") and pos_total == Decimal("0.00"):
            issues.append(
                ReconciliationIssue(
                    id=f"{run_id}:woo-missing-pos:{business_date}",
                    run_id=run_id,
                    severity="high",
                    category="missing_entry",
                    title=f"WooCommerce orders not reflected in POS online sales for {business_date}",
                    evidence=[
                        f"WooCommerce completed orders totaling {woo_total:.2f} on {business_date} have no matching POS online sales line."
                    ],
                    recommended_action="Confirm the e-commerce sales were posted to POS or accounting before the close.",
                    related_transaction_ids=[txn.id for txn in woo_transactions],
                )
            )
            continue
        issues.append(
            ReconciliationIssue(
                id=f"{run_id}:woo-vs-pos:{business_date}",
                run_id=run_id,
                severity="medium",
                category="total_mismatch",
                title=f"WooCommerce orders disagree with POS online sales for {business_date}",
                evidence=[
                    f"WooCommerce orders {woo_total:.2f}; POS online sales {pos_total:.2f}; differs by {difference:.2f}."
                ],
                recommended_action="Compare order list against POS online tender and account for refunds or unfulfilled orders.",
                related_transaction_ids=[
                    txn.id for txn in woo_transactions + pos_transactions
                ],
            )
        )
    return issues


def _detect_fuel_invoice_variances(
    run_id: str, transactions: List[CanonicalTransaction]
) -> List[ReconciliationIssue]:
    issues: List[ReconciliationIssue] = []
    for transaction in transactions:
        if transaction.source_type != "fuel_invoice":
            continue
        metadata = transaction.metadata or {}
        gallons_value = metadata.get("gallons")
        received_gallons = metadata.get("received_gallons")
        expected_amount = metadata.get("expected_amount")

        if gallons_value is not None and received_gallons not in (None, ""):
            try:
                invoice_gallons = Decimal(str(gallons_value))
                delivered_gallons = Decimal(str(received_gallons))
            except Exception:
                invoice_gallons = delivered_gallons = None
            if invoice_gallons is not None and invoice_gallons != delivered_gallons:
                gallons_difference = abs(invoice_gallons - delivered_gallons)
                issues.append(
                    ReconciliationIssue(
                        id=f"{run_id}:fuel-gallons:{transaction.id}",
                        run_id=run_id,
                        severity="high",
                        category="total_mismatch",
                        title=f"Fuel invoice gallons differ from received delivery for {transaction.business_date}",
                        evidence=[
                            f"Invoice {transaction.external_ref}: invoice gallons {invoice_gallons}, received {delivered_gallons}, off by {gallons_difference}."
                        ],
                        recommended_action="Compare the BOL or stick reading with the fuel invoice before paying.",
                        related_transaction_ids=[transaction.id],
                    )
                )

        if expected_amount not in (None, ""):
            try:
                invoice_amount = Decimal(transaction.amount)
                expected = Decimal(str(expected_amount))
            except Exception:
                invoice_amount = expected = None
            if invoice_amount is not None and invoice_amount != expected:
                amount_difference = abs(invoice_amount - expected)
                issues.append(
                    ReconciliationIssue(
                        id=f"{run_id}:fuel-amount:{transaction.id}",
                        run_id=run_id,
                        severity="medium",
                        category="suspicious_total",
                        title=f"Fuel invoice amount differs from expected payable for {transaction.business_date}",
                        evidence=[
                            f"Invoice {transaction.external_ref}: amount {invoice_amount:.2f}, expected {expected:.2f}, off by {amount_difference:.2f}."
                        ],
                        recommended_action="Verify the contracted price, taxes, and freight against the supplier invoice.",
                        related_transaction_ids=[transaction.id],
                    )
                )
    return issues


def _detect_lottery_settlement_mismatches(
    run_id: str, transactions: List[CanonicalTransaction]
) -> List[ReconciliationIssue]:
    pos_lottery = _group_by_date(
        txn for txn in transactions if txn.source_type == "pos_daily" and txn.tender_type == "lottery"
    )
    settlement_lottery = _group_by_date(
        txn for txn in transactions if txn.source_type == "lottery_settlement" and txn.tender_type == "lottery"
    )
    issues: List[ReconciliationIssue] = []
    for business_date, pos_transactions in pos_lottery.items():
        settlement_transactions = settlement_lottery.get(business_date, [])
        if not settlement_transactions:
            continue
        pos_total = _sum_amount(pos_transactions)
        settlement_total = _sum_amount(settlement_transactions)
        if pos_total != settlement_total:
            difference = abs(pos_total - settlement_total)
            issues.append(
                ReconciliationIssue(
                    id=f"{run_id}:lottery:{business_date}",
                    run_id=run_id,
                    severity="high",
                    category="total_mismatch",
                    title=f"Lottery settlement differs from POS lottery net for {business_date}",
                    evidence=[
                        f"POS lottery net {pos_total:.2f}; lottery settlement {settlement_total:.2f}; differs by {difference:.2f}."
                    ],
                    recommended_action="Compare lottery shift report, commission, payouts, and settlement statement.",
                    related_transaction_ids=[txn.id for txn in pos_transactions + settlement_transactions],
                )
            )
    return issues
