"""Inference for the locked 12-feature cash-flow stress classifier."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from config import (
    ARTIFACT_PATH,
    MIN_ACTIVE_MONTHS,
    MIN_VALID_TRANSACTIONS,
    MODEL_VERSION,
    SUFFICIENT_ACTIVE_MONTHS,
    SUFFICIENT_VALID_TRANSACTIONS,
)
from features.pipeline import FEATURE_NAMES, build_features_for_profile
from model.artifact import load_artifact
from schemas import BorrowerInput, CashflowResult, Reason


class CashflowEngine:
    def __init__(self, artifact_path: str | Path = ARTIFACT_PATH):
        self.artifact = load_artifact(Path(artifact_path))
        if tuple(self.artifact["feature_names"]) != FEATURE_NAMES:
            raise ValueError(
                "artifact feature layout does not match the locked 12-feature pipeline"
            )
        if not hasattr(self.artifact["model"], "predict_proba"):
            raise ValueError("cash-flow stress artifact must be a probability classifier")

    def assess(self, profile: BorrowerInput) -> CashflowResult:
        vector = build_features_for_profile(profile)
        context = vector.context
        active_months = int(context["active_months"])
        transaction_count = int(context["operating_transaction_count"])
        warnings: list[str] = []
        if context["duplicate_count"]:
            warnings.append("DUPLICATE_TRANSACTIONS_IGNORED")
        if context["future_transaction_count"]:
            warnings.append("POST_CUTOFF_TRANSACTIONS_IGNORED")
        if context["self_declared_income_share"] > 0:
            warnings.append("UNVERIFIED_SELF_DECLARED_INCOME_EXCLUDED")

        if active_months < MIN_ACTIVE_MONTHS or transaction_count < MIN_VALID_TRANSACTIONS:
            return CashflowResult(
                component="cashflow",
                version=MODEL_VERSION,
                score=None,
                status="INSUFFICIENT",
                confidence=round(self._confidence(vector), 3),
                features=self._public_features(vector),
                stress_probability=None,
                reasons=(
                    Reason(
                        "CF14",
                        "NEUTRAL",
                        0.0,
                        "There is insufficient usable history for a cash-flow stress assessment.",
                    ),
                    Reason(
                        "CF15",
                        "NEUTRAL",
                        0.0,
                        "Usable transaction or active-month coverage is below the configured minimum.",
                    ),
                ),
                warnings=tuple(warnings),
            )

        frame = pd.DataFrame([vector.model_values()], columns=FEATURE_NAMES)
        stress_probability = float(
            np.clip(self.artifact["model"].predict_proba(frame)[0, 1], 0, 1)
        )
        # Person 4's existing readiness formula expects higher = healthier.
        # Keep the model output explicit and expose this inverse only as a
        # compatibility score; it is not a second model.
        health_score = 100.0 * (1.0 - stress_probability)
        status = (
            "SUFFICIENT"
            if active_months >= SUFFICIENT_ACTIVE_MONTHS
            and transaction_count >= SUFFICIENT_VALID_TRANSACTIONS
            and context["data_coverage"] >= 0.70
            else "DEGRADED"
        )
        return CashflowResult(
            component="cashflow",
            version=MODEL_VERSION,
            score=round(health_score, 3),
            status=status,
            confidence=round(self._confidence(vector), 3),
            features=self._public_features(vector),
            stress_probability=round(stress_probability, 6),
            reasons=self._reasons(vector, stress_probability),
            warnings=tuple(dict.fromkeys(warnings)),
        )

    @staticmethod
    def _confidence(vector) -> float:
        context = vector.context
        months = min(float(context["active_months"]) / 12.0, 1.0)
        transactions = min(float(context["operating_transaction_count"]) / 100.0, 1.0)
        verified = float(context["verified_transaction_share"])
        coverage = float(context["data_coverage"])
        return float(
            np.clip(
                0.30 * months
                + 0.25 * transactions
                + 0.25 * verified
                + 0.20 * coverage,
                0,
                1,
            )
        )

    @staticmethod
    def _public_features(vector) -> dict:
        values = {
            name: None if value is None else round(float(value), 6)
            for name, value in vector.values.items()
        }
        return {
            **values,
            "active_months": int(vector.context["active_months"]),
            "eligible_transaction_count": int(
                vector.context["eligible_transaction_count"]
            ),
            "operating_transaction_count": int(
                vector.context["operating_transaction_count"]
            ),
            "data_coverage": round(float(vector.context["data_coverage"]), 6),
            "conservative_monthly_inflow_paise": round(
                float(vector.context["conservative_monthly_inflow"]), 2
            ),
            "median_monthly_business_expense_paise": round(
                float(vector.context["median_monthly_business_expense_paise"]), 2
            ),
            "verified_transaction_share": round(
                float(vector.context["verified_transaction_share"]), 6
            ),
            "self_declared_income_share": round(
                float(vector.context["self_declared_income_share"]), 6
            ),
        }

    @staticmethod
    def _reasons(vector, probability: float) -> tuple[Reason, ...]:
        values = vector.values
        reasons = [
            Reason(
                "CF20",
                "NEGATIVE" if probability >= 0.5 else "POSITIVE",
                round(probability, 3),
                f"Estimated probability of cash-flow stress in the next 90 days is {probability:.1%}.",
            )
        ]
        if (values["six_month_inflow_trend"] or 0) < 0:
            reasons.append(
                Reason("CF06", "NEGATIVE", 0.0, "Business inflow declined over the latest six-month window.")
            )
        if (values["negative_cashflow_month_ratio"] or 0) > 0.20:
            reasons.append(
                Reason("CF13", "NEGATIVE", 0.0, "Negative operating cash-flow months occur frequently in the observation window.")
            )
        if (values["inflow_volatility"] or 0) > 0.40:
            reasons.append(
                Reason("CF07", "NEGATIVE", 0.0, "Business inflow is highly volatile month to month.")
            )
        if (values["median_operating_surplus_paise"] or 0) > 0:
            reasons.append(
                Reason("CF03", "POSITIVE", 0.0, "Median monthly operating surplus is positive.")
            )
        return tuple(reasons)


def predict(
    profile: BorrowerInput, artifact_path: str | Path = ARTIFACT_PATH
) -> CashflowResult:
    return CashflowEngine(artifact_path).assess(profile)
