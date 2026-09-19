"""Conservative field-name policy for keeping likely PII out of profiling and prompts."""

import re

PII_TOKENS = {
    "address",
    "birth",
    "customer_name",
    "dob",
    "email",
    "first_name",
    "full_name",
    "last_name",
    "password",
    "phone",
    "secret",
    "ssn",
    "token",
    "username",
}


def is_possible_pii(field_name: str) -> bool:
    normalized = re.sub(r"[^a-z0-9]+", "_", field_name.lower()).strip("_")
    return normalized in PII_TOKENS or any(
        normalized.startswith(f"{token}_") or normalized.endswith(f"_{token}")
        for token in PII_TOKENS
    )
