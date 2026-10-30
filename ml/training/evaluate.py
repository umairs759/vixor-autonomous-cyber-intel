"""VIXOR - Model evaluation report (T-033)."""

from __future__ import annotations

import json
import os

try:
    from .train_models import train_and_evaluate
except ImportError:  # pragma: no cover - script execution fallback
    from train_models import train_and_evaluate  # type: ignore[import-not-found]

ARTIFACT_DIR = os.path.join(os.path.dirname(__file__), "..", "artifacts")


def evaluate() -> dict:
    """Return the stored evaluation metadata report."""
    metadata_path = os.path.join(ARTIFACT_DIR, "metadata.json")
    if os.path.exists(metadata_path):
        with open(metadata_path, encoding="utf-8") as fh:
            return json.load(fh)
    return train_and_evaluate()


if __name__ == "__main__":
    report = evaluate()
    print(json.dumps(report.get("results", {}), indent=2))
