import re
from typing import Optional


COMPANY_WORDS = {
    "co": "",
    "company": "",
    "inc": "",
    "llc": "",
    "ltd": "",
}


def normalize_payee(value: str) -> str:
    cleaned = value.strip().lower()
    cleaned = cleaned.replace("&", " and ")
    cleaned = re.sub(r"[^a-z0-9]+", " ", cleaned)
    tokens = [COMPANY_WORDS.get(token, token) for token in cleaned.split()]
    tokens = [token for token in tokens if token]
    return "-".join(tokens)


def create_duplicate_key(
    business_date: str,
    amount: str,
    payee_key: Optional[str],
    external_ref: Optional[str],
) -> str:
    if external_ref:
        return f"ref|{external_ref.strip()}"
    return f"{business_date}|{amount}|{payee_key or 'unknown-payee'}"

