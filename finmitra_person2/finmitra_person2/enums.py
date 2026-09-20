from enum import StrEnum


class Direction(StrEnum):
    CREDIT = "CREDIT"
    DEBIT = "DEBIT"


class TransactionStatus(StrEnum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    REVERSED = "REVERSED"


class AssessmentStatus(StrEnum):
    SUFFICIENT = "SUFFICIENT"
    DEGRADED = "DEGRADED"
    INSUFFICIENT = "INSUFFICIENT"


class ReasonDirection(StrEnum):
    POSITIVE = "POSITIVE"
    NEGATIVE = "NEGATIVE"
    NEUTRAL = "NEUTRAL"
