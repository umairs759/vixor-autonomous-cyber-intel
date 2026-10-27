"""VIXOR — ML scoring Celery tasks (T-032 to T-036).

Feature extraction, RandomForest/XGBoost scoring, and SHAP TreeExplainer
explanations. No LLM is used for scoring or narratives.
"""

from typing import Any

from app.core.logging import get_logger
from app.deps import get_db_session
from app.models.finding import Finding
from app.models.finding_score import FindingScore
from app.services.ml.features import extract_features
from app.services.ml.scoring import ScoringService
from app.workers.celery_app import celery_app

logger = get_logger("workers.ml")
scoring_service = ScoringService()


@celery_app.task(name="app.workers.tasks_ml.score_findings")  # type: ignore[untyped-decorator]
def score_findings(finding_ids: list[str]) -> dict[str, Any]:
    """Score findings using the trained ML model with SHAP explanations.

    Falls back to rule-based scoring if the model is unavailable.
    """
    db = get_db_session()
    try:
        scored: list[dict[str, Any]] = []
        for finding_id in finding_ids:
            finding = db.query(Finding).filter(Finding.id == finding_id).first()
            if not finding:
                continue

            features = extract_features(
                finding.evidence or {},
                cvss_base=finding.cvss or 0.0,
            )
            score_result = scoring_service.score(features)

            score = (
                db.query(FindingScore)
                .filter(FindingScore.finding_id == finding_id)
                .first()
            )
            if score:
                score.risk_score = score_result.get("risk_score", 0.0)
                score.risk_class = score_result.get("risk_class", "low")
                score.model_version = score_result.get("model_version", "fallback")
                score.features = score_result.get("features", {})
                score.shap_values = score_result.get("shap_values", {})
                score.narrative = score_result.get("narrative", "")
                score.scored_by = score_result.get("scored_by", "fallback")
            else:
                score = FindingScore(
                    finding_id=finding_id,
                    risk_score=score_result.get("risk_score", 0.0),
                    risk_class=score_result.get("risk_class", "low"),
                    model_version=score_result.get("model_version", "fallback"),
                    features=score_result.get("features", {}),
                    shap_values=score_result.get("shap_values", {}),
                    narrative=score_result.get("narrative", ""),
                    scored_by=score_result.get("scored_by", "fallback"),
                )
                db.add(score)
            db.commit()

            scored.append(
                {
                    "finding_id": finding_id,
                    "risk_score": score_result.get("risk_score", 0.0),
                    "risk_class": score_result.get("risk_class", "low"),
                    "scored_by": score_result.get("scored_by", "fallback"),
                    "narrative": score_result.get("narrative", ""),
                }
            )

        return {"scored": scored, "count": len(scored)}
    except Exception as exc:
        logger.exception("ml_scoring_failed", error=str(exc))
        return {"scored": [], "count": 0, "error": str(exc)}
    finally:
        db.close()
