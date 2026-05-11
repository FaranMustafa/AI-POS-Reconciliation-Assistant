from collections import defaultdict
from decimal import Decimal
from typing import Dict, Iterable, List

from reconciliation.normalization import create_duplicate_key
from reconciliation.types import CanonicalTransaction, ReconciliationIssue


SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}


def run_reconciliation(run_id: str, transactions: List[CanonicalTransaction]) -> List[ReconciliationIssue]:
    issues: List[ReconciliationIssue] = []
    issues.extend(_detect_card_settlement_gaps(run_id, transactions))
    issues.extend(_detect_duplicate_entries(run_id, transactions))
    issues.extend(_detect_suspended_sales(run_id, transactions))
    issues.extend(_detect_lottery_settlement_mismatches(run_id, transactions))
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


def _detect_duplicate_entries(
    run_id: str, transactions: List[CanonicalTransaction]
) -> List[ReconciliationIssue]:
    buckets: Dict[str, List[CanonicalTransaction]] = defaultdict(list)
    for transaction in transactions:
        if transaction.category not in {"expense", "invoice"}:
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
