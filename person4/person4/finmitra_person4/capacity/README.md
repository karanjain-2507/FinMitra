# Capacity & Affordability Engine (Person 4)

## Overview

The **Capacity Engine** is Person 4's core subsystem in FinMitra. It deterministically calculates a borrower's monthly affordability in INR (rupee amounts) and subjects their budget to 5 standardized stress test scenarios.

> **Key Architectural Principle**: Capacity does **NOT** determine creditworthiness or generate an ML credit score (`score` is always `None`). It determines whether the borrower can financially handle an additional installment and produces rupee-denominated affordability outputs.

---

## Input Parameters

The engine consumes the canonical `CapacityInput` parameters (all amounts in INR, non-negative floats):

| Field | Type | Description |
|---|---|---|
| `conservative_monthly_inflow` | `float` | Conservative monthly cash inflow (from cash-flow pipeline) |
| `essential_household_expense` | `float` | Monthly household essential expenditure |
| `essential_business_expense` | `float` | Monthly business essential expenditure |
| `existing_formal_emis` | `float` | Active bank/NBFC EMI obligations |
| `existing_informal_installments` | `float` | Active informal installments (chit funds, supplier credit) |
| `income_volatility` | `float` | Coefficient of variation of monthly income (0.0–1.0) |
| `lowest_recent_monthly_inflow` | `float` | Lowest observed monthly inflow across statement window |
| `available_balance_buffer` | `float` | Liquid buffer at assessment time |
| `outstanding_delinquent_amount` | `float` | Overdue delinquent balance |
| `requested_loan_amount` | `Optional[float]` | Requested principal (optional) |
| `annual_interest_rate` | `Optional[float]` | Annual interest rate as decimal, e.g. 0.14 for 14% (optional) |
| `tenure_months` | `Optional[int]` | Loan tenure in months (optional) |

---

## Primary Calculations

### 1. Conservative Monthly Surplus

$$\text{Existing Obligations} = \text{Existing Formal EMIs} + \text{Existing Informal Installments}$$

$$\text{Monthly Surplus} = \text{Conservative Inflow} - \text{Household Essentials} - \text{Business Essentials} - \text{Existing Obligations}$$

### 2. Safe EMI Range

$$\text{Safe EMI}_{\min} = \max(0, \text{Monthly Surplus} \times \text{safe\_emi\_min\_factor})$$

$$\text{Safe EMI}_{\max} = \max(0, \text{Monthly Surplus} \times \text{safe\_emi\_max\_factor})$$

- Default policy factors: $\text{min} = 40\%$, $\text{max} = 50\%$.
- Negative or zero surplus always yields $\text{Safe EMI} = ₹0$.

### 3. Maximum Principal Formula

Derived by inverting the standard amortizing EMI formula:

For $r > 0$ (where $r = \frac{\text{annual\_rate}}{12}$, $n = \text{tenure months}$):

$$P = \text{Safe EMI}_{\max} \times \frac{(1 + r)^n - 1}{r(1 + r)^n}$$

For $r = 0$:

$$P = \text{Safe EMI}_{\max} \times n$$

Computed for tenures of **6, 12, and 18 months**.

---

## Standardized Stress Tests

| Test | Name | Scenario | Pass Criterion |
|---|---|---|---|
| **ST1** | `income_drop_20pct` | Inflow drops 20% for 3 months | Stressed safe EMI $\ge 40\%$ baseline |
| **ST2** | `zero_income_month` | Inflow drops to ₹0 for 1 month | Available buffer $\ge$ 1 month deficit |
| **ST3** | `expense_increase_30pct` | Essential expenses rise 30% | Stressed safe EMI $\ge 40\%$ baseline |
| **ST4** | `informal_installment_continues` | Retains informal obligations | Surplus remains $> 0$ |
| **ST5** | `seasonal_low_income` | Inflow drops to `lowest_recent_monthly_inflow` | Low-inflow surplus $\ge 0$ |

---

## Status Classification

| Status | Trigger Condition |
|---|---|
| `SUFFICIENT_CAPACITY` | Positive surplus, $\text{safe\_emi\_max} \ge ₹3,000$ |
| `LIMITED_CAPACITY` | Positive surplus, $0 < \text{safe\_emi\_max} < ₹3,000$ |
| `NO_CAPACITY` | Surplus $\le 0$ or safe EMI $= 0$ |
| `BLOCKED` | Repayment engine flagged `new_credit_blocked = True` |
| `INSUFFICIENT_DATA` | Required parameters missing |

---

## Usage Example

```python
from capacity.engine import CapacityEngine
from common.schemas import CapacityInput

inp = CapacityInput(
    conservative_monthly_inflow=28000.0,
    essential_household_expense=10000.0,
    essential_business_expense=7500.0,
    existing_formal_emis=1500.0,
    existing_informal_installments=1000.0,
    income_volatility=0.12,
    lowest_recent_monthly_inflow=23000.0,
    available_balance_buffer=15000.0,
    outstanding_delinquent_amount=0.0,
    requested_loan_amount=40000.0,
    annual_interest_rate=0.14,
    tenure_months=12,
)

result = CapacityEngine.assess(inp, new_credit_blocked=False)

print("Safe EMI:", result.safe_emi.minimum, "-", result.safe_emi.maximum)
print("Status:", result.status)
print("Max Principal (12m):", result.max_principal["12_months"])
```
