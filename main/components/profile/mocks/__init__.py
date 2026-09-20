"""
mocks/__init__.py

Mock component implementations for integration development.

⚠️  MOCKS ONLY — Do NOT use these in production.

These exist solely to allow the Capacity Engine and Profile Assembler to be
developed and tested before the real Evidence, Cash-Flow, and Repayment
engines are available.

When the real engines are ready, replace calls to mock_evidence(),
mock_cashflow(), mock_repayment() with calls to the real engine APIs.
The Capacity Engine and Profile Assembler do NOT need to change.
"""
from mocks.evidence import mock_evidence
from mocks.cashflow import mock_cashflow
from mocks.repayment import mock_repayment

__all__ = ["mock_evidence", "mock_cashflow", "mock_repayment"]
