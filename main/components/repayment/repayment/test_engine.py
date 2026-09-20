"""Repayment engine tests."""

from __future__ import annotations

import json
import unittest
from datetime import date
from pathlib import Path

from common.schemas import BorrowerInput, Loan, Repayment, Transaction
from repayment.engine import assess
from repayment.matching import SELF_DECLARED, match_repayments
from repayment.schedule import expected_amount_as_of, expected_installments_as_of

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures"


def load_fixture(name: str) -> BorrowerInput:
    payload = json.loads((FIXTURES / name).read_text())
    return BorrowerInput.model_validate(payload)


class ScheduleTests(unittest.TestCase):
    def test_expected_installments_exclude_future_dues(self) -> None:
        loan = Loan(
            loan_id="L001",
            lender_id="L1",
            issue_date=date(2025, 12, 1),
            principal_amount=30000,
            installment_amount=5000,
            installment_frequency="MONTHLY",
            number_of_installments=6,
            first_due_date=date(2026, 1, 1),
        )
        expected = expected_installments_as_of(loan, date(2026, 4, 15))
        self.assertEqual(len(expected), 4)
        self.assertEqual([item.due_date for item in expected], [
            date(2026, 1, 1),
            date(2026, 2, 1),
            date(2026, 3, 1),
            date(2026, 4, 1),
        ])
        self.assertEqual(expected_amount_as_of(loan, date(2026, 4, 15)), 20000)


class EngineFixtureTests(unittest.TestCase):
    def test_strong_borrower(self) -> None:
        result = assess(load_fixture("strong_borrower.json"))
        self.assertEqual(result.component, "repayment")
        self.assertEqual(result.version, "1.0.0")
        self.assertEqual(result.status, "COMPLETED")
        self.assertFalse(result.new_credit_blocked)
        self.assertIsNone(result.hard_cap)
        self.assertGreaterEqual(result.score or 0, 80)
        self.assertGreaterEqual(result.confidence, 0.85)
        self.assertEqual(result.features["digitally_matched_repayment_ratio"], 1.0)
        self.assertTrue(any(reason.code == "RP10" for reason in result.reasons))

    def test_unpaid_overdue_loan(self) -> None:
        result = assess(load_fixture("unpaid_loan.json"))
        self.assertEqual(result.status, "SEVERELY_UNPAID")
        self.assertTrue(result.new_credit_blocked)
        self.assertEqual(result.hard_cap, 35)
        self.assertTrue(any(reason.code == "RP01" for reason in result.reasons))

    def test_current_loan(self) -> None:
        result = assess(load_fixture("seasonal_business.json"))
        self.assertEqual(result.status, "CURRENT")
        self.assertFalse(result.new_credit_blocked)
        self.assertEqual(result.features["payments_expected"], 4)
        self.assertEqual(result.features["payments_made"], 4)
        self.assertEqual(result.features["on_time_payment_ratio"], 1.0)

    def test_thin_evidence(self) -> None:
        thin = assess(load_fixture("thin_file.json"))
        strong = assess(load_fixture("strong_borrower.json"))
        self.assertEqual(thin.status, "INSUFFICIENT_EVIDENCE")
        self.assertLess(thin.confidence, strong.confidence)
        self.assertEqual(thin.features["digitally_matched_repayment_ratio"], 0.0)


class ConstructedCaseTests(unittest.TestCase):
    def test_partially_repaid_overdue_loan(self) -> None:
        profile = BorrowerInput(
            borrower_id="B-PARTIAL",
            evaluation_date=date(2026, 4, 15),
            informal_loans=[
                Loan(
                    loan_id="L-PARTIAL",
                    lender_id="LENDER-02",
                    issue_date=date(2025, 12, 1),
                    principal_amount=30000,
                    installment_amount=5000,
                    installment_frequency="MONTHLY",
                    number_of_installments=6,
                    first_due_date=date(2026, 1, 1),
                    declared_status="OVERDUE",
                    relationship_type="INFORMAL",
                )
            ],
            repayment_claims=[
                Repayment(
                    repayment_id="R1",
                    loan_id="L-PARTIAL",
                    date=date(2026, 1, 1),
                    amount=5000,
                    transaction_id="T1",
                    source="BANK_STATEMENT",
                    verified=True,
                    confidence=0.9,
                ),
                Repayment(
                    repayment_id="R2",
                    loan_id="L-PARTIAL",
                    date=date(2026, 2, 1),
                    amount=5000,
                    transaction_id="T2",
                    source="BANK_STATEMENT",
                    verified=True,
                    confidence=0.9,
                ),
            ],
            transactions=[
                Transaction(
                    transaction_id="T1",
                    date=date(2026, 1, 1),
                    amount=5000,
                    direction="DEBIT",
                    category="LOAN_REPAYMENT",
                    counterparty_id="LENDER-02",
                    source="BANK_STATEMENT",
                    verified=True,
                ),
                Transaction(
                    transaction_id="T2",
                    date=date(2026, 2, 1),
                    amount=5000,
                    direction="DEBIT",
                    category="LOAN_REPAYMENT",
                    counterparty_id="LENDER-02",
                    source="BANK_STATEMENT",
                    verified=True,
                ),
            ],
        )
        result = assess(profile)
        self.assertEqual(result.status, "DELINQUENT")
        self.assertTrue(result.new_credit_blocked)
        self.assertEqual(result.hard_cap, 35)
        self.assertGreater(result.features["outstanding_principal"], 0)

    def test_contradiction_is_not_verified_repayment(self) -> None:
        profile = BorrowerInput(
            borrower_id="B-CONTRA",
            evaluation_date=date(2026, 4, 15),
            informal_loans=[
                Loan(
                    loan_id="L-CONTRA",
                    lender_id="LENDER-03",
                    issue_date=date(2026, 1, 1),
                    principal_amount=15000,
                    installment_amount=5000,
                    installment_frequency="MONTHLY",
                    number_of_installments=3,
                    first_due_date=date(2026, 2, 1),
                    declared_status="CURRENT",
                    relationship_type="FRIEND",
                )
            ],
            repayment_claims=[
                Repayment(
                    repayment_id="R-ONLY-CLAIM",
                    loan_id="L-CONTRA",
                    date=date(2026, 2, 1),
                    amount=5000,
                    transaction_id=None,
                    source="SELF_DECLARED",
                    verified=False,
                    confidence=0.2,
                )
            ],
            transactions=[],
        )
        matches = match_repayments(profile)
        self.assertTrue(all(match.match_method == SELF_DECLARED for match in matches))
        result = assess(profile)
        self.assertEqual(result.features["total_amount_repaid"], 0)
        self.assertEqual(result.features["contradictory_declarations"], 0)
        self.assertEqual(result.features["digitally_matched_repayment_ratio"], 0.0)
        self.assertNotEqual(result.status, "CURRENT")
        self.assertNotEqual(result.status, "COMPLETED")
        self.assertFalse(any(reason.code == "RP08" for reason in result.reasons))

    def test_cash_flow_does_not_override_delinquency(self) -> None:
        profile = load_fixture("unpaid_loan.json")
        profile = profile.model_copy(
            update={
                "cash_flow": {
                    "cash_flow_score": 95,
                    "cash_flow_confidence": 0.99,
                }
            }
        )
        result = assess(profile)
        self.assertEqual(result.status, "SEVERELY_UNPAID")
        self.assertTrue(result.new_credit_blocked)
        self.assertTrue(any("cash_flow" in warning for warning in result.warnings))


if __name__ == "__main__":
    unittest.main()
