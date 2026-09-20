from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

import joblib


def save_versioned_artifact(payload: dict, artifact_path: Path, metadata: dict, metadata_path: Path) -> None:
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    for path in (artifact_path, metadata_path):
        if path.exists():
            shutil.copy2(path, path.with_name(f"{path.stem}.backup-{timestamp}{path.suffix}"))
    joblib.dump(payload, artifact_path)
    metadata_path.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_artifact(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"model artifact not found: {path}; run python train.py")
    return joblib.load(path)
