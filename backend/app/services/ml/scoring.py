"""VIXOR — Scoring service (T-035).

ML risk scoring using trained RandomForest/XGBoost models.
Falls back to rule-based scoring if model is missing.
"""

import os
from typing import Any

import joblib
import numpy as np

from app.core.logging import get_logger
from app.services.ml.features import feature_names

logger = get_logger("ml.scoring")


class ScoringService:
    """ML risk scoring service with fallback rule-based scorer."""

    def __init__(
        self,
        model_path: str | None = None,
        model_version: str = "rf-v1.0.0",
    ):
        self.model_path = model_path
        self.model_version = model_version
        self.model = None
        self.model_type = None
        self._load_model()

    def _load_model(self) -> None:
        """Load the trained model from disk."""
        if not self.model_path or not os.path.exists(self.model_path):
            logger.warning(
                "model file not found, using fallback scorer",
                path=self.model_path,
            )
            return

        try:
            self.model = joblib.load(self.model_path)
            self.model_type = "rf" if "rf" in self.model_path.lower() else "xgb"
            logger.info(
                "model loaded",
                path=self.model_path,
                type=self.model_type,
            )
        except Exception as exc:
            logger.exception("model load failed", path=self.model_path, error=str(exc))
            self.model = None

    def score(
        self,
        features: dict[str, Any],
    ) -> dict[str, Any]:
        """Score a finding using the ML model or fallback.

        Returns:
            Dict with risk_score (0-100), risk_class, scored_by, features, shap_values.
        """
        if self.model is not None:
            return self._score_with_model(features)
        else:
            return self._score_with_fallback(features)

    def _score_with_model(
        self,
        features: dict[str, Any],
    ) -> dict[str, Any]:
        """Score using the trained ML model."""
        feature_vec = np.array([[features.get(name, 0.0) for name in feature_names()]])

        try:
            # Get prediction (0-1 probability)
            if hasattr(self.model, "predict_proba"):
                prob = self.model.predict_proba(feature_vec)[0][1]
            else:
                prob = float(self.model.predict(feature_vec)[0])

            risk_score = float(prob * 100.0)
            risk_score = max(0.0, min(100.0, risk_score))

            risk_class = self._score_to_class(risk_score)

            # SHAP values (if TreeExplainer available)
            shap_values = self._compute_shap(feature_vec)

            return {
                "risk_score": risk_score,
                "risk_class": risk_class,
                "model_version": self.model_version,
                "features": features,
                "shap_values": shap_values,
                "scored_by": "ml",
            }
        except Exception as exc:
            logger.exception("model scoring failed", error=str(exc))
            return self._score_with_fallback(features)

    def _score_with_fallback(
        self,
        features: dict[str, Any],
    ) -> dict[str, Any]:
        """Fallback rule-based scoring when ML model is unavailable."""
        # Weighted rule-based score
        weights = {
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

        # SHAP-like contributions (simplified)
        shap_values = {}
        for feature, weight in weights.items():
            val = features.get(feature, 0.0)
            if isinstance(val, bool):
                val = 1.0 if val else 0.0
            shap_values[feature] = round(float(val) * weight * 100.0, 2)

        risk_class = self._score_to_class(score)

        return {
            "risk_score": round(score, 2),
            "risk_class": risk_class,
            "model_version": "rule-based-v1.0.0",
            "features": features,
            "shap_values": shap_values,
            "scored_by": "fallback",
        }

    @staticmethod
    def _score_to_class(score: float) -> str:
        """Convert risk score to risk class."""
        if score >= 75:
            return "critical"
        elif score >= 50:
            return "high"
        elif score >= 25:
            return "medium"
        else:
            return "low"

    def _compute_shap(
        self,
        feature_vec: np.ndarray,
    ) -> dict[str, float]:
        """Compute SHAP values using TreeExplainer if available."""
        try:
            import shap

            explainer = shap.TreeExplainer(self.model)
            shap_values = explainer.shap_values(feature_vec)

            if isinstance(shap_values, list):
                # Multi-class: take the positive class
                shap_values = shap_values[1]

            shap_dict = {}
            for i, name in enumerate(feature_names()):
                shap_dict[name] = round(float(shap_values[0][i]), 4)

            return shap_dict
        except Exception:  # noqa: BLE001 - SHAP explainer may not be available
            # Return zero SHAP values if explainer not available
            return {name: 0.0 for name in feature_names()}
