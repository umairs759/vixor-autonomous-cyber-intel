"""Unit tests for feature extraction (T-034, T-052)."""

from app.services.ml.features import extract_features, feature_names


def test_feature_extraction_basic():
    finding = {"evidence": {"port": "443"}, "severity_raw": "high", "cvss": 7.5}
    features = extract_features(finding)
    assert set(features.keys()) == set(feature_names())
    assert features["cvss_base"] == 0.75
    assert features["template_severity"] == 0.75
    assert features["service_port_risk"] == 0.5


def test_feature_extraction_defaults():
    features = extract_features({})
    assert features["cvss_base"] == 0.0
    assert features["internet_exposed"] == 1.0
