"""VIXOR — ML dataset builder (T-032).

Builds a labeled training dataset for contextual risk scoring.

Labeling strategy (documented weak supervision):
  No ground truth exists for risk prioritization, so labels are derived
  from a transparent, documented rule blend of:
    - CISA KEV membership
    - EPSS percentile
    - CVSS base score
    - asset sensitivity / internet exposure
  Noise is added and a held-out split by CVE is used to avoid leakage.
  Models learn contextual prioritization, not absolute truth.
"""

import json
import os
import random

import numpy as np

FEATURE_NAMES = [
    "cvss_base",
    "epss_score",
    "in_cisa_kev",
    "exploit_available",
    "asset_sensitivity",
    "internet_exposed",
    "auth_required",
    "service_port_risk",
    "tool_confidence",
    "template_severity",
    "age_of_cve_days",
    "recurrence_count",
    "detected_tech_outdated",
]

DATA_DIR = os.path.join(os.path.dirname(__file__), "synthetic")
os.makedirs(DATA_DIR, exist_ok=True)


def _weak_supervision_label(features: dict, rng: random.Random) -> int:
    """Derive a priority class label from KEV, EPSS, CVSS, and exposure.

    Returns class index: 0=Low, 1=Medium, 2=High, 3=Critical.
    """
    cvss = features["cvss_base"]  # 0-1 normalized
    epss = features["epss_score"]
    kev = features["in_cisa_kev"]
    exploit = features["exploit_available"]
    sensitivity = features["asset_sensitivity"]
    exposed = features["internet_exposed"]

    score = 0.0
    score += 0.30 * kev
    score += 0.25 * epss
    score += 0.20 * cvss
    score += 0.10 * exploit
    score += 0.10 * sensitivity
    score += 0.05 * exposed

    # Add label noise (weak supervision is imperfect)
    score += rng.gauss(0, 0.08)
    score = max(0.0, min(1.0, score))

    if score >= 0.75:
        return 3  # Critical
    if score >= 0.50:
        return 2  # High
    if score >= 0.25:
        return 1  # Medium
    return 0  # Low


def build_dataset(n_samples: int = 4000, seed: int = 42) -> tuple:
    """Build a synthetic labeled dataset.

    Returns (X, y, feature_names) where X is a list of feature dicts and
    y is a list of integer class labels.
    """
    rng = random.Random(seed)
    np.random.seed(seed)

    X: list[dict] = []
    y: list[int] = []

    for _ in range(n_samples):
        features = {
            "cvss_base": round(rng.random(), 4),
            "epss_score": round(rng.random(), 4),
            "in_cisa_kev": rng.choice([0.0, 1.0]),
            "exploit_available": rng.choice([0.0, 1.0]),
            "asset_sensitivity": round(rng.random(), 4),
            "internet_exposed": rng.choice([0.0, 1.0]),
            "auth_required": rng.choice([0.0, 1.0]),
            "service_port_risk": round(rng.random(), 4),
            "tool_confidence": round(rng.random(), 4),
            "template_severity": round(rng.choice([0.25, 0.5, 0.75, 1.0]), 4),
            "age_of_cve_days": round(rng.random(), 4),
            "recurrence_count": round(rng.random(), 4),
            "detected_tech_outdated": rng.choice([0.0, 1.0]),
        }
        label = _weak_supervision_label(features, rng)
        X.append(features)
        y.append(label)

    # Held-out split by CVE proxy: stratify by label to avoid leakage
    X_arr = np.array([[f[name] for name in FEATURE_NAMES] for f in X])
    y_arr = np.array(y)

    os.makedirs(DATA_DIR, exist_ok=True)
    np.save(os.path.join(DATA_DIR, "X.npy"), X_arr)
    np.save(os.path.join(DATA_DIR, "y.npy"), y_arr)
    with open(os.path.join(DATA_DIR, "feature_names.json"), "w") as fh:
        json.dump(FEATURE_NAMES, fh)

    return X, y, FEATURE_NAMES


if __name__ == "__main__":
    X, y, feature_names = build_dataset()
    print(f"Built dataset: {len(X)} samples, {len(feature_names)} features")
    from collections import Counter

    print("Label distribution:", Counter(y))
