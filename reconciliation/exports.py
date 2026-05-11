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

