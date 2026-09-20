# FinMitra — Person 4 Subsystem
## Capacity Engine + Profile Assembler + Combined CLI + Integration Tests

**FinMitra** evaluates borrowers across four independent tracks. This repository contains the complete implementation of **Person 4's ownership area**:

1. **Capacity / Affordability Engine** (`capacity/`)
2. **Stress-Testing Engine** (`capacity/stress_tests.py`)
3. **Profile Assembler** (`fusion/profile_assembler.py`)
4. **Integration Adapters & Contracts** (`fusion/adapters.py`, `common/schemas.py`)
5. **Combined CLI** (`run_profile.py`)
6. **Mock Components** (`mocks/`)
7. **Four Standard Demo Fixtures** (`fixtures/`)
8. **Unit, Contract, and Integration Test Suite** (`tests/`, `capacity/test_engine.py`, `fusion/test_profile.py`)

---

## 1. System Architecture

```text
  Evidence Engine (P1) ──────────┐
  Cash-Flow Model (P2) ──────────┤
  Repayment Engine (P3) ─────────┤
                                 ▼
                    ┌─────────────────────────┐
                    │     Capacity Engine     │
                    │  (Affordability math &  │
                    │      Stress Tests)      │
                    └────────────┬────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │    Profile Assembler    │
                    │  (Readiness + Policies) │
                    └────────────┬────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │ FinMitra Credit Profile │
                    └─────────────────────────┘
```

### Core Architecture Rules:
- **Capacity does NOT produce a credit score**: `score` is always `null`. It produces rupee-denominated affordability figures (`safe_emi`, `max_principal`).
- **Readiness Index**: Calculated strictly as $0.55 \times \text{Cashflow Score} + 0.45 \times \text{Repayment Score}$. Evidence and Capacity are **never** averaged into readiness.
- **Repayment Hard Block**: If `new_credit_blocked = true`, `safe_emi` is forced to `₹0` and `readiness_index` is capped at `35`.
- **Evidence Grade D**: Caps `readiness_index` at `75`.
- **Insufficient History**: Sets `readiness_index = null`.
- **Confidence Fusion**: Overall confidence is the **minimum** of all four component confidences ($\min(\text{EV}, \text{CF}, \text{RP}, \text{CP})$).

---

## 2. Directory Structure

```text
finmitra_person4/
├── README.md
├── pyproject.toml
├── requirements.txt
├── common/
│   ├── __init__.py
│   ├── schemas.py          # Shared Pydantic contracts & component output models
│   ├── config.py           # Configurable CapacityPolicy defaults and loader
│   ├── reason_codes.py     # CPxx, EVxx, CFxx, RPxx reason codes
│   ├── validation.py       # Non-negative, ratio, finite guards & contract validator
│   └── policies.py         # Readiness index, policy ceilings & confidence fusion
├── capacity/
│   ├── __init__.py
│   ├── engine.py           # CapacityEngine.assess() orchestrator
│   ├── calculations.py     # Pure math: surplus, safe EMI, EMI, max principal
│   ├── stress_tests.py     # 5 deterministic stress scenarios
│   ├── test_engine.py      # Unit tests for capacity math & stress tests
│   └── README.md           # Detailed capacity engine documentation
├── fusion/
│   ├── __init__.py
│   ├── profile_assembler.py # ProfileAssembler.assemble()
│   ├── adapters.py          # Strict contract validation adapters
│   └── test_profile.py      # Profile assembler & policy unit tests
├── mocks/
│   ├── __init__.py
│   ├── evidence.py         # Mock Evidence Engine
│   ├── cashflow.py         # Mock Cashflow Model
│   └── repayment.py        # Mock Repayment Engine
├── fixtures/
│   ├── strong_borrower.json   # Kirana store owner with positive surplus & EMI headroom
│   ├── seasonal_business.json # Seasonal farmer with harvest gaps & low-inflow stress test
│   ├── thin_file.json         # 2 months data, insufficient history -> readiness = null
│   └── unpaid_loan.json       # High income + delinquent supplier loan -> Safe EMI = 0
├── run_profile.py          # Combined CLI entrypoint
└── tests/
    ├── __init__.py
    ├── test_integration.py # End-to-end pipeline integration tests
    ├── test_contracts.py   # Malformed output rejection tests
    └── test_fixtures.py    # Fixture validation tests
```

---

## 3. Quick Start & CLI Usage

### Requirements
- Python 3.9+ (Python 3.11+ recommended)
- `pydantic>=2.5`
- `pytest>=7.4`

### Installation
```bash
pip install -r requirements.txt
```

### Running the Profile CLI
```bash
# Evaluate Strong Borrower (Kirana Store)
python run_profile.py --input fixtures/strong_borrower.json --pretty

# Evaluate Seasonal Farmer
python run_profile.py --input fixtures/seasonal_business.json --pretty

# Evaluate Thin-File Borrower (Readiness is null)
python run_profile.py --input fixtures/thin_file.json --pretty

# Evaluate Unpaid Loan (Hard Block: Safe EMI = 0, Readiness capped at 35)
python run_profile.py --input fixtures/unpaid_loan.json --pretty

# Save to output file
python run_profile.py --input fixtures/strong_borrower.json --output profile.json
```

---

## 4. Four Standard Demo Scenarios

| Scenario | Borrower Type | Key Signal | Expected Behavior |
|---|---|---|---|
| **Borrower 1** (`strong_borrower.json`) | Stable kirana store | Completed supplier loan, steady UPI | `SUFFICIENT_CAPACITY`, Readiness $\approx 81.15$, Safe EMI ₹3,200–₹4,000 |
| **Borrower 2** (`seasonal_business.json`) | Seasonal farmer | Large harvest inflows, low trough | Evaluated on low-income trough; not automatically blocked |
| **Borrower 3** (`thin_file.json`) | Thin-file vendor | 2 months transaction data | `insufficient_history = true` $\rightarrow$ `readiness_index: null` |
| **Borrower 4** (`unpaid_loan.json`) | High income, unpaid loan | ₹25,000 overdue on supplier loan | `new_credit_blocked = true` $\rightarrow$ Safe EMI = ₹0, Readiness $\le 35$ |

---

## 5. Running the Test Suite

Run all 158 tests covering unit math, stress tests, policy ceilings, contract validation, and end-to-end integration:

```bash
pytest -v
```

---

## 6. How Other Teams Integrate

When Person 1, 2, and 3 finish their engines, integration requires zero rewrites:
1. Ensure the engine produces an object adhering to `EvidenceResult`, `CashflowResult`, or `RepaymentResult` from `common.schemas`.
2. In `run_profile.py` or your orchestrator, pass the real engine outputs directly to `ProfileAssembler.assemble(evidence, cashflow, repayment, capacity)`.
