import csv
import io
from typing import Iterable

from reconciliation.types import ReconciliationIssue


ISSUE_EXPORT_HEADERS = [
    "Severity",
    "Category",
    "Title",
    "Evidence",
    "Recommended Action",
    "Related Transactions",
]


def issues_to_csv(issues: Iterable[ReconciliationIssue]) -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(ISSUE_EXPORT_HEADERS)
    for issue in issues:
        writer.writerow(
            [
                issue.severity,
                issue.category,
                issue.title,
                " | ".join(issue.evidence),
                issue.recommended_action,
                " | ".join(issue.related_transaction_ids),
            ]
        )
    return output.getvalue()


ADJUSTMENT_EXPORT_HEADERS = [
    "Issue ID",
    "Severity",
    "Category",
    "Suggested Account",
    "Memo",
    "Action",
    "Related Transactions",
]


_CATEGORY_TO_ACCOUNT = {
    "settlement_gap": "Card Clearing",
    "missing_entry": "Suspense - Unmatched Settlement",
    "duplicate_entry": "Vendor AP - Duplicate Review",
    "total_mismatch": "Sales Suspense",
    "suspicious_total": "Fuel Inventory - Variance",
    "unresolved_suspended_sale": "Suspense - POS Suspended Sales",
}


def issues_to_accounting_adjustment_csv(issues: Iterable[ReconciliationIssue]) -> str:
    """Render a journal-entry oriented CSV for accountants to ingest."""

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(ADJUSTMENT_EXPORT_HEADERS)
    for issue in issues:
        suggested_account = _CATEGORY_TO_ACCOUNT.get(
            issue.category, "Suspense - Reconciliation"
        )
        memo = issue.title
        if issue.evidence:
            memo = f"{memo} — {issue.evidence[0]}"
        writer.writerow(
            [
                issue.id,
                issue.severity,
                issue.category,
                suggested_account,
                memo,
                issue.recommended_action,
                " | ".join(issue.related_transaction_ids),
            ]
        )
    return output.getvalue()

