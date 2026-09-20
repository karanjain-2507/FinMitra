"""FastAPI thin wrapper around the FinMitra integrated pipeline.

Run from the main/ directory:
    uvicorn api_server:app --reload --port 8000
"""

from __future__ import annotations

import csv
import io
import json
import sys
from decimal import Decimal
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError

# Ensure the finmitra package is importable when run from main/
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from finmitra.demo import build_demo
from finmitra.assessment_store import assessment_store
from finmitra.passport import passport_service
from finmitra.passport.schemas import PassportGoalClaim
from finmitra.runner import AssessmentError, assess
from finmitra.schemas import IntegratedBorrowerInput
from finmitra.what_if import WhatIfEngine, baseline_from_assessment
from finmitra.what_if.schemas import Goal

app = FastAPI(title="FinMitra API", version="1.0.0")

MAX_REQUEST_BYTES = 2 * 1024 * 1024


@app.middleware("http")
async def limit_request_size(request: Request, call_next):
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > MAX_REQUEST_BYTES:
                return JSONResponse(status_code=413, content={"detail": "Request body is too large"})
        except ValueError:
            return JSONResponse(status_code=400, content={"detail": "Invalid Content-Length header"})
    return await call_next(request)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _run(raw: dict[str, Any]) -> dict[str, Any]:
    """Validate and run the pipeline, surfacing errors as HTTP exceptions."""
    try:
        profile = IntegratedBorrowerInput.model_validate(raw)
        result = assess(profile)
        result["assessment_id"] = assessment_store.put(result)
        return result
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except AssessmentError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


class WhatIfRequest(BaseModel):
    """Opaque reference to an authoritative server-owned assessment plus a goal."""

    model_config = ConfigDict(extra="forbid")

    assessment_id: str = Field(min_length=16, max_length=128)
    goal: Goal


class PassportIssueRequest(BaseModel):
    """Issue a credential from a server-owned assessment and optional goal."""

    model_config = ConfigDict(extra="forbid")

    assessment_id: str = Field(min_length=16, max_length=128)
    goal: Goal | None = None


class PassportVerifyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    credential_id: str = Field(min_length=8, max_length=64)


GOAL_ADAPTER = TypeAdapter(Goal)


def _plan_assessment(assessment: dict[str, Any], goal: Goal) -> dict[str, Any]:
    try:
        baseline = baseline_from_assessment(assessment)
        # Pydantic serializes Decimal as strings by default. What If's public
        # contract keeps financial values numeric for formatting/localization.
        planned = WhatIfEngine.plan(baseline, goal)
        return jsonable_encoder(
            planned.model_dump(mode="python"),
            custom_encoder={Decimal: float},
        )
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except AssessmentError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


def _plan(profile: IntegratedBorrowerInput, goal: Goal) -> dict[str, Any]:
    try:
        return _plan_assessment(assess(profile), goal)
    except AssessmentError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


async def _csv_assessment_input(
    file: UploadFile,
    borrower_id: str,
    business_name: str,
    evaluation_date: str,
    household_expense: float,
    balance_buffer: float,
    source_type: str,
) -> IntegratedBorrowerInput:
    """Build the canonical input shared by CSV assessment and planning."""
    content = await file.read()
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = content.decode("latin-1")

    rows = list(csv.DictReader(io.StringIO(text)))
    if not rows:
        raise HTTPException(status_code=400, detail="CSV contains no data rows")

    raw: dict[str, Any] = {
        "borrower_id": borrower_id.strip() or "BORROWER-001",
        "evaluation_date": evaluation_date,
        "sources": [
            {
                "source_id": f"CSV-{source_type}-01",
                "source_type": source_type,
                "records": rows,
                "metadata": {"filename": file.filename or "upload.csv"},
            }
        ],
        "informal_loans": [],
        "repayment_claims": [],
        "capacity_context": {
            "essential_household_expense": household_expense,
            "available_balance_buffer": balance_buffer,
        },
    }
    if business_name.strip():
        raw["business_name"] = business_name.strip()
    try:
        return IntegratedBorrowerInput.model_validate(raw)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/api/demo/{scenario}")
async def demo_endpoint(scenario: str) -> dict[str, Any]:
    """Run one of the three bundled demo scenarios."""
    if scenario not in ("strong", "unpaid", "thin"):
        raise HTTPException(
            status_code=400,
            detail="scenario must be one of: strong, unpaid, thin",
        )
    return _run(build_demo(scenario))


@app.post("/api/assess")
async def assess_json(payload: dict[str, Any]) -> dict[str, Any]:
    """Accept a full IntegratedBorrowerInput JSON and return the assessment."""
    return _run(payload)


@app.post("/api/assess/csv")
async def assess_csv(
    file: UploadFile = File(...),
    borrower_id: str = Form("BORROWER-001"),
    business_name: str = Form(""),
    evaluation_date: str = Form(...),
    household_expense: float = Form(0.0),
    balance_buffer: float = Form(0.0),
    source_type: str = Form("BANK_STATEMENT"),
) -> dict[str, Any]:
    """Accept a CSV bank statement and assemble an IntegratedBorrowerInput."""
    profile = await _csv_assessment_input(
        file,
        borrower_id,
        business_name,
        evaluation_date,
        household_expense,
        balance_buffer,
        source_type,
    )
    result = assess(profile)
    result["assessment_id"] = assessment_store.put(result)
    return result


@app.post("/api/what-if")
async def what_if_json(payload: WhatIfRequest) -> dict[str, Any]:
    """Plan only from an immutable assessment snapshot owned by the server."""
    assessment = assessment_store.get(payload.assessment_id)
    if assessment is None:
        raise HTTPException(status_code=404, detail="Assessment not found or expired")
    return _plan_assessment(assessment, payload.goal)


@app.post("/api/what-if/demo/{scenario}")
async def what_if_demo(scenario: str, goal: dict[str, Any]) -> dict[str, Any]:
    """Plan from one of the server-owned demonstration assessments."""
    if scenario not in ("strong", "unpaid", "thin"):
        raise HTTPException(
            status_code=400,
            detail="scenario must be one of: strong, unpaid, thin",
        )
    try:
        parsed_goal = GOAL_ADAPTER.validate_python(goal)
        profile = IntegratedBorrowerInput.model_validate(build_demo(scenario))
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _plan(profile, parsed_goal)


@app.post("/api/what-if/csv")
async def what_if_csv(
    file: UploadFile = File(...),
    goal: str = Form(...),
    borrower_id: str = Form("BORROWER-001"),
    business_name: str = Form(""),
    evaluation_date: str = Form(...),
    household_expense: float = Form(0.0),
    balance_buffer: float = Form(0.0),
    source_type: str = Form("BANK_STATEMENT"),
) -> dict[str, Any]:
    """Reassess an uploaded statement and plan without trusting client results."""
    try:
        parsed_goal = GOAL_ADAPTER.validate_python(json.loads(goal))
    except (json.JSONDecodeError, ValidationError) as exc:
        raise HTTPException(status_code=422, detail=f"Invalid goal: {exc}") from exc
    profile = await _csv_assessment_input(
        file,
        borrower_id,
        business_name,
        evaluation_date,
        household_expense,
        balance_buffer,
        source_type,
    )
    return _plan(profile, parsed_goal)


@app.post("/api/passports", status_code=201)
async def issue_passport(payload: PassportIssueRequest) -> dict[str, Any]:
    """Issue a signed, selectively disclosed credential from an assessment."""
    assessment = assessment_store.get(payload.assessment_id)
    if assessment is None:
        raise HTTPException(status_code=404, detail="Assessment not found or expired")
    goal_claim = None
    if payload.goal is not None:
        baseline = baseline_from_assessment(assessment)
        plan = WhatIfEngine.plan(baseline, payload.goal)
        goal_claim = PassportGoalClaim(
            goal_type=plan.goal.type,
            outcome=plan.outcome,
            deadline_months=plan.goal.deadline_months,
        )
    credential = passport_service.issue(assessment, goal_claim=goal_claim)
    return credential.model_dump(mode="json")


@app.get("/api/passports/{credential_id}")
async def get_passport(credential_id: str) -> dict[str, Any]:
    credential = passport_service.get(credential_id)
    if credential is None:
        raise HTTPException(status_code=404, detail="Credential not found")
    return credential.model_dump(mode="json")


@app.post("/api/passports/verify")
async def verify_passport(payload: PassportVerifyRequest) -> dict[str, Any]:
    """Verify signature and expiry, returning only disclosed claims."""
    return passport_service.verify(payload.credential_id.strip()).model_dump(mode="json")


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "pipeline_version": "1.0.0"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("api_server:app", host="0.0.0.0", port=8000, reload=True)
