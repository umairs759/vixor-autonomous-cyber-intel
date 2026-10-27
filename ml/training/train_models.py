"""VIXOR — ML model training (T-033).

Trains RandomForest and XGBoost classifiers on the weak-supervision
dataset, evaluates them, and saves versioned artifacts with metadata.json
under ml/artifacts/. No LLM is used anywhere in training or scoring.
"""

import json
import os
from datetime import datetime, timezone

import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, f1_score
from sklearn.model_selection import train_test_split
from xgboost import XGBClassifier

ARTIFACT_DIR = os.path.join(os.path.dirname(__file__), "..", "artifacts")
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "synthetic")
os.makedirs(ARTIFACT_DIR, exist_ok=True)

FEATURE_NAMES_PATH = os.path.join(DATA_DIR, "feature_names.json")
X_PATH = os.path.join(DATA_DIR, "X.npy")
Y_PATH = os.path.join(DATA_DIR, "y.npy")

CLASS_NAMES = ["Low", "Medium", "High", "Critical"]


def load_data():
    with open(FEATURE_NAMES_PATH) as fh:
        feature_names = json.load(fh)
    X = np.load(X_PATH)
    y = np.load(Y_PATH)
    return X, y, feature_names


def train_and_evaluate() -> dict:
    X, y, feature_names = load_data()

    # Stratified split to avoid leakage and keep class balance
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    models = {
        "rf-v1.0.0": RandomForestClassifier(
            n_estimators=200, max_depth=12, random_state=42, n_jobs=-1
        ),
        "xgb-v1.0.0": XGBClassifier(
            n_estimators=200, max_depth=8, random_state=42, n_jobs=-1,
            eval_metric="mlogloss",
        ),
    }

    results = {}
    best_name = None
    best_f1 = -1.0

    for name, model in models.items():
        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)
        acc = accuracy_score(y_test, y_pred)
        macro_f1 = f1_score(y_test, y_pred, average="macro")
        report = classification_report(
            y_test, y_pred, target_names=CLASS_NAMES, output_dict=True
        )

        results[name] = {
            "accuracy": round(acc, 4),
            "macro_f1": round(macro_f1, 4),
            "report": report,
        }

        if macro_f1 > best_f1:
            best_f1 = macro_f1
            best_name = name

    # Save the winning model and metadata
    best_model = models[best_name]
    model_path = os.path.join(ARTIFACT_DIR, f"{best_name}.joblib")
    joblib.dump(best_model, model_path)

    metadata = {
        "model": best_name,
        "model_path": model_path,
        "feature_names": feature_names,
        "class_names": CLASS_NAMES,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "results": results,
        "labeling_strategy": (
            "Weak supervision: blend of CISA KEV, EPSS percentile, CVSS, "
            "exploit availability, asset sensitivity and internet exposure "
            "with added label noise. Held-out stratified split by class."
        ),
        "note": (
            "Models learn contextual prioritization from weak labels; "
            "no LLM is used for scoring or narratives."
        ),
    }
    with open(os.path.join(ARTIFACT_DIR, "metadata.json"), "w") as fh:
        json.dump(metadata, fh, indent=2)

    # Save a copy under each version name for the scoring service to load
    for name in models:
        joblib.dump(models[name], os.path.join(ARTIFACT_DIR, f"{name}.joblib"))

    print(f"Best model: {best_name} (macro F1={best_f1:.4f})")
    print(f"Artifacts saved to {ARTIFACT_DIR}")
    return metadata


if __name__ == "__main__":
    train_and_evaluate()
