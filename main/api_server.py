"""FastAPI thin wrapper around the FinMitra integrated pipeline.

Run from the main/ directory:
    uvicorn api_server:app --reload --port 8000
"""

from __future__ import annotations

import csv
import io
import sys
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError

# Ensure the finmitra package is importable when run from main/
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from finmitra.demo import build_demo
from finmitra.runner import AssessmentError, assess
from finmitra.schemas import IntegratedBorrowerInput

app = FastAPI(title="FinMitra API", version="1.0.0")

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
        return assess(profile)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except AssessmentError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


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
    content = await file.read()
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = content.decode("latin-1")

    reader = csv.DictReader(io.StringIO(text))
    rows = list(reader)
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

    return _run(raw)


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "pipeline_version": "1.0.0"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("api_server:app", host="0.0.0.0", port=8000, reload=True)
