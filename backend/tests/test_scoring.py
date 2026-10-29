"""Unit tests for scoring service (T-035)."""

from app.services.ml.scoring import ScoringService


def test_fallback_scoring():
    svc = ScoringService(model_path=None)
    features = {"cvss_base": 0.9, "in_cisa_kev": 1.0}
    result = svc.score(features)
    assert result["scored_by"] in ("ml", "fallback")
    assert 0 <= result["risk_score"] <= 100
    assert "narrative" in result
    assert set(result["shap_values"].keys())


def test_score_to_class():
    assert ScoringService._score_to_class(80) == "critical"
    assert ScoringService._score_to_class(10) == "low"
