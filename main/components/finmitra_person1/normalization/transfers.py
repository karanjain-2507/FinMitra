"""
Transfer and Own-Account Movement Detection.
Identifies internal fund transfers, self-transfers, and contra entries
so they do not falsely inflate business income or expense figures.
"""
from __future__ import annotations
import re
from typing import Optional, Tuple

from ..enums import TransactionCategory, CategorySource, VerificationLevel


TRANSFER_PATTERNS = [
    r"\bself\s*transfer\b",
    r"\bown\s*acc(?:ount)?\b",
    r"\btrf\s*to\s*self\b",
    r"\btransfer\s*to\s*savings\b",
    r"\btransfer\s*to\s*current\b",
    r"\bto\s*own\s*a/c\b",
    r"\bcontra\b",
    r"\bsweep\s*(?:in|out|to|from)\b",
    r"\bfd\s*(?:create|close|sweep)\b",
    r"\binter[\s-]*account\b",
    r"\binternal\s*trf\b"
]


def is_transfer_narration(narration: Optional[str]) -> bool:
    """Check if narration text indicates an internal transfer."""
    if not narration:
        return False
    text = narration.lower()
    for pattern in TRANSFER_PATTERNS:
        if re.search(pattern, text):
            return True
    return False


def is_self_counterparty(
    counterparty: Optional[str],
    borrower_name: Optional[str],
    business_name: Optional[str]
) -> bool:
    """Check if the counterparty matches the borrower's own identity."""
    if not counterparty:
        return False
    c_lower = counterparty.strip().lower()
    if c_lower in ("self", "own account", "own acc", "myself"):
        return True
    if borrower_name and len(borrower_name.strip()) >= 3:
        b_lower = borrower_name.strip().lower()
        if c_lower == b_lower or f"to {b_lower}" in c_lower or f"from {b_lower}" in c_lower:
            return True
    if business_name and len(business_name.strip()) >= 3:
        biz_lower = business_name.strip().lower()
        if c_lower == biz_lower or f"to {biz_lower}" in c_lower or f"from {biz_lower}" in c_lower:
            return True
    return False


def evaluate_transfer(
    narration: Optional[str],
    counterparty: Optional[str],
    borrower_name: Optional[str] = None,
    business_name: Optional[str] = None
) -> Tuple[bool, Optional[TransactionCategory], Optional[CategorySource], Optional[float]]:
    """
    Evaluate whether a record represents an internal/self transfer.
    Returns (is_transfer, category, category_source, confidence).
    """
    if is_transfer_narration(narration):
        return True, TransactionCategory.TRANSFER, CategorySource.NARRATION_RULE, 0.90

    if is_self_counterparty(counterparty, borrower_name, business_name):
        return True, TransactionCategory.TRANSFER, CategorySource.COUNTERPARTY_PATTERN, 0.85

    return False, None, None, None
