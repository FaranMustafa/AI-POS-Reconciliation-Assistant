from dataclasses import dataclass, field
from typing import Dict, List, Optional, Union


MetadataValue = Union[str, int, float, bool, None]


@dataclass(frozen=True)
class CanonicalTransaction:
    id: str
    source_import_id: str
    source_type: str
    business_date: str
    posted_at: str
    category: str
    tender_type: str
    external_ref: Optional[str]
    payee_key: Optional[str]
    description: str
    amount: str
    metadata: Dict[str, MetadataValue] = field(default_factory=dict)


@dataclass(frozen=True)
class ReconciliationIssue:
    id: str
    run_id: str
    severity: str
    category: str
    title: str
    evidence: List[str]
    recommended_action: str
    related_transaction_ids: List[str]

