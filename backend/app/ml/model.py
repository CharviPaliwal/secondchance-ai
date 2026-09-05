"""Model loading and action-conditioned recovery probability inference."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

from app.ml.features import FEATURE_VERSION, build_features

MODEL_PATH = Path(__file__).resolve().parents[2] / "model" / "recovery_policy.joblib"
MODEL_VERSION = "SecondChance Recovery Policy v1.0.0"
CANDIDATE_ACTIONS = ("RETRY_LATER", "SEND_REMINDER", "UPDATE_PAYMENT_METHOD", "ESCALATE_TO_HUMAN", "STOP_RECOVERY")


@lru_cache(maxsize=1)
def load_model() -> Any | None:
    try:
        import joblib
        return joblib.load(MODEL_PATH) if MODEL_PATH.exists() else None
    except (ImportError, OSError, ValueError):
        return None


def metadata() -> dict[str, Any]:
    model = load_model()
    if not model:
        return {"model_status": "ML_FALLBACK", "model_version": "deterministic-fallback", "feature_version": FEATURE_VERSION}
    return {**model["metadata"], "model_status": "ML_AVAILABLE"}


def predict_action_probabilities(transaction: dict[str, Any], customer: dict[str, Any]) -> dict[str, float] | None:
    """Estimate P(recovery success | observable transaction, candidate action)."""
    model = load_model()
    if not model:
        return None
    rows = [build_features(transaction, customer, action) for action in CANDIDATE_ACTIONS]
    probabilities = model["pipeline"].predict_proba(rows)
    classes = list(model["pipeline"].classes_)
    success_index = classes.index(1) if 1 in classes else 0
    return {action: round(float(probabilities[index][success_index]), 4) for index, action in enumerate(CANDIDATE_ACTIONS)}


def predict_batch_action_probabilities(cases: list[tuple[dict[str, Any], dict[str, Any]]]) -> list[dict[str, float]] | None:
    """Vectorized inference for static dataset aggregation and simulation."""
    model = load_model()
    if not model:
        return None
    rows = [build_features(transaction, customer, action) for transaction, customer in cases for action in CANDIDATE_ACTIONS]
    probabilities = model["pipeline"].predict_proba(rows)
    classes = list(model["pipeline"].classes_)
    success_index = classes.index(1) if 1 in classes else 0
    return [{action: round(float(probabilities[index * len(CANDIDATE_ACTIONS) + action_index][success_index]), 4) for action_index, action in enumerate(CANDIDATE_ACTIONS)} for index in range(len(cases))]
