"""VIXOR - Scoring service (T-035).

ML risk scoring using the trained XGBoost model (ml/artifacts/xgb-v1.0.0).
Falls back to rule-based scoring if the model is missing.
SHAP TreeExplainer produces feature contributions; narratives are
deterministic templates (no LLM).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import joblib  # type: ignore[import-untyped]
import numpy as np

from app.core.logging import get_logger
from app.services.ml.explain import generate_narrative
from app.services.ml.features import feature_names

logger = get_logger("ml.scoring")

_REPO_ROOT = Path(__file__).resolve().parents[4]
_DEFAULT_MODEL_PATH = _REPO_ROOT / "ml" / "artifacts" / "xgb-v1.0.0.joblib"


class ScoringService:
    """ML risk scoring service with fallback rule-based scorer."""

    def __init__(
        self,
        model_path: str | None = None,
        model_version: str = "xgb-v1.0.0",
    ):
        if model_path is None and _DEFAULT_MODEL_PATH.exists():
            model_path = str(_DEFAULT_MODEL_PATH)
        self.model_path = model_path
        self.model_version = model_version
        self.model: Any = None
        self.model_type: str | None = None
        self._load_model()

    def _load_model(self) -> None:
        if not self.model_path or not os.path.exists(self.model_path):
            logger.warning("model file not found, using fallback scorer", path=self.model_path)
            return
        try:
            self.model = joblib.load(self.model_path)
            self.model_type = "xgb" if "xgb" in self.model_path.lower() else "rf"
            logger.info("model loaded", path=self.model_path, type=self.model_type)
        except Exception as exc:
            logger.exception("model load failed", path=self.model_path, error=str(exc))
            self.model = None

    def score(self, features: dict[str, Any]) -> dict[str, Any]:
        if self.model is not None:
            return self._score_with_model(features)
        return self._score_with_fallback(features)

    def _score_with_model(self, features: dict[str, Any]) -> dict[str, Any]:
        feature_vec = np.array([[features.get(name, 0.0) for name in feature_names()]], dtype=float)
        try:
            if hasattr(self.model, "predict_proba"):
                proba = self.model.predict_proba(feature_vec)[0]
                # Weighted class index -> 0..100 risk score (classes ordered Low..Critical)
                risk_score = float(sum(i * p for i, p in enumerate(proba)) / max(len(proba) - 1, 1) * 100.0)
            else:
                pred = int(self.model.predict(feature_vec)[0])
                risk_score = float(pred / 3.0 * 100.0)

            risk_score = max(0.0, min(100.0, risk_score))
            risk_class = self._score_to_class(risk_score)
            shap_values = self._compute_shap(feature_vec, risk_score)
            narrative = generate_narrative(risk_score, shap_values, features)

            return {
                "risk_score": round(risk_score, 2),
                "risk_class": risk_class,
                "model_version": self.model_version,
                "features": features,
                "shap_values": shap_values,
                "scored_by": "ml",
                "narrative": narrative,
            }
        except Exception as exc:
            logger.exception("model scoring failed", error=str(exc))
            return self._score_with_fallback(features)

    def _score_with_fallback(self, features: dict[str, Any]) -> dict[str, Any]:
        weights: dict[str, float] = {
            "cvss_base": 0.25,
            "in_cisa_kev": 0.20,
            "epss_score": 0.15,
            "exploit_available": 0.10,
            "asset_sensitivity": 0.10,
            "internet_exposed": 0.05,
            "auth_required": 0.05,
            "service_port_risk": 0.05,
            "tool_confidence": 0.02,
            "template_severity": 0.03,
            "detected_tech_outdated": 0.03,
        }

        score = 0.0
        for feature, weight in weights.items():
            val = features.get(feature, 0.0)
            if isinstance(val, bool):
                val = 1.0 if val else 0.0
            score += float(val) * weight * 100.0

        score = max(0.0, min(100.0, score))

        shap_values: dict[str, float] = {}
        for feature, weight in weights.items():
            val = features.get(feature, 0.0)
            if isinstance(val, bool):
                val = 1.0 if val else 0.0
            shap_values[feature] = round(float(val) * weight * 100.0, 2)

        risk_class = self._score_to_class(score)
        narrative = generate_narrative(score, shap_values, features)

        return {
            "risk_score": round(score, 2),
            "risk_class": risk_class,
            "model_version": "rule-based-v1.0.0",
            "features": features,
            "shap_values": shap_values,
            "scored_by": "fallback",
            "narrative": narrative,
        }

    @staticmethod
    def _score_to_class(score: float) -> str:
        if score >= 75:
            return "critical"
        if score >= 50:
            return "high"
        if score >= 25:
            return "medium"
        return "low"

    def _compute_shap(self, feature_vec: np.ndarray, risk_score: float) -> dict[str, float]:
        try:
            import shap  # type: ignore[import-untyped]

            explainer = shap.TreeExplainer(self.model)
            shap_values = explainer.shap_values(feature_vec)

            if isinstance(shap_values, list):
                # Pick the class closest to the predicted risk level
                class_idx = min(int(risk_score / 33.4), len(shap_values) - 1)
                shap_values = shap_values[class_idx]

            shap_dict: dict[str, float] = {}
            for i, name in enumerate(feature_names()):
                shap_dict[name] = round(float(shap_values[0][i]), 4)
            return shap_dict
        except Exception:  # noqa: BLE001
            return {name: 0.0 for name in feature_names()}