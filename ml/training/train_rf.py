"""VIXOR - RandomForest training entrypoint (T-033)."""

from __future__ import annotations

try:
    from .train_models import train_and_evaluate
except ImportError:  # pragma: no cover - script execution fallback
    from train_models import train_and_evaluate  # type: ignore[import-not-found]


def train_random_forest() -> dict:
    """Train and persist the RandomForest model (part of versioned run)."""
    return train_and_evaluate()


if __name__ == "__main__":
    train_random_forest()
