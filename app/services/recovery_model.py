"""ML recovery model trained on synthetic data for the SecondChance prototype.

This is a synthetic-data prototype and must be retrained and validated on real
historical recovery outcomes before production use.
"""

from __future__ import annotations

import hashlib
import threading
from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from app.services.data_generator import generate_dataset

CANDIDATE_ACTIONS = (
    "RETRY_NOW",
    "RETRY_LATER",
    "SEND_REMINDER",
    "UPDATE_PAYMENT_METHOD",
)

NUMERIC_FEATURES = (
    "amount",
    "attempt_count",
    "payment_success_rate",
    "previous_recovery_success_rate",
    "contacts_last_7_days",
    "tenure_days",
    "total_transactions",
    "successful_transactions",
    "average_transaction_amount",
    "transaction_hour",
    "transaction_day_of_week",
)
CATEGORICAL_FEATURES = (
    "payment_method",
    "failure_reason",
    "merchant_category",
    "candidate_action",
)
FEATURES = NUMERIC_FEATURES + CATEGORICAL_FEATURES

_MODEL_LOCK = threading.Lock()
_MODEL_BUNDLE: dict[str, Any] | None = None


def _stable_seed(transaction_id: str, action: str) -> int:
    digest = hashlib.sha256(f"{transaction_id}:{action}".encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big", signed=False) % (2**32)


def _timestamp_parts(value: str | datetime) -> tuple[int, int]:
    timestamp = datetime.fromisoformat(value) if isinstance(value, str) else value
    return timestamp.hour, timestamp.weekday()


def _feature_row(transaction: dict[str, Any], customer: dict[str, Any], action: str) -> dict[str, Any]:
    hour, day_of_week = _timestamp_parts(transaction["transaction_timestamp"])
    return {
        "amount": float(transaction["amount"]),
        "attempt_count": int(transaction["attempt_count"]),
        "payment_success_rate": float(customer["payment_success_rate"]),
        "previous_recovery_success_rate": float(customer["previous_recovery_success_rate"]),
        "contacts_last_7_days": int(customer["contacts_last_7_days"]),
        "tenure_days": int(customer["tenure_days"]),
        "total_transactions": int(customer["total_transactions"]),
        "successful_transactions": int(customer["successful_transactions"]),
        "average_transaction_amount": float(customer["average_transaction_amount"]),
        "transaction_hour": hour,
        "transaction_day_of_week": day_of_week,
        "payment_method": str(transaction["payment_method"]),
        "failure_reason": str(transaction["failure_reason"]),
        "merchant_category": str(transaction["merchant_category"]),
        "candidate_action": action,
    }


def _build_training_frame() -> pd.DataFrame:
    transactions, customer_profiles, simulation_truth = generate_dataset(count=10000, seed=20260902)
    customers = {item["customer_id"]: item for item in customer_profiles}
    truth_by_id = {item["transaction_id"]: item for item in simulation_truth}
    rows: list[dict[str, Any]] = []
    for transaction in transactions:
        truth = truth_by_id[transaction["transaction_id"]]
        customer = customers[transaction["customer_id"]]
        probabilities = truth["action_success_probabilities"]
        for action in CANDIDATE_ACTIONS:
            probability = float(probabilities[action])
            recovered = int(np.random.default_rng(_stable_seed(transaction["transaction_id"], action)).binomial(1, probability))
            rows.append({
                **_feature_row(transaction, customer, action),
                "transaction_id": transaction["transaction_id"],
                "recovered": recovered,
            })
    return pd.DataFrame(rows)


def _split_by_transaction(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    transaction_ids = sorted(frame["transaction_id"].unique())
    train_end = int(len(transaction_ids) * 0.60)
    validation_end = int(len(transaction_ids) * 0.80)
    train_ids = set(transaction_ids[:train_end])
    validation_ids = set(transaction_ids[train_end:validation_end])
    test_ids = set(transaction_ids[validation_end:])
    train = frame[frame["transaction_id"].isin(train_ids)].copy()
    validation = frame[frame["transaction_id"].isin(validation_ids)].copy()
    test = frame[frame["transaction_id"].isin(test_ids)].copy()
    return train, validation, test


def _one_hot_encoder() -> OneHotEncoder:
    try:
        return OneHotEncoder(handle_unknown="ignore", sparse_output=False)
    except TypeError:
        return OneHotEncoder(handle_unknown="ignore", sparse=False)


def _preprocessor(scale_numeric: bool) -> ColumnTransformer:
    numeric = StandardScaler() if scale_numeric else "passthrough"
    return ColumnTransformer(
        transformers=[
            ("numeric", numeric, list(NUMERIC_FEATURES)),
            ("categorical", _one_hot_encoder(), list(CATEGORICAL_FEATURES)),
        ],
        remainder="drop",
        sparse_threshold=0.0,
    )


def _build_pipeline(classifier: Any, *, scale_numeric: bool) -> Pipeline:
    return Pipeline([
        ("preprocessor", _preprocessor(scale_numeric)),
        ("classifier", classifier),
    ])


def _pr_auc(y_true: pd.Series, probabilities: np.ndarray) -> float:
    if len(np.unique(y_true)) < 2:
        return 0.0
    return float(average_precision_score(y_true, probabilities))


def _test_metrics(y_true: pd.Series, probabilities: np.ndarray) -> dict[str, float]:
    both_classes = len(np.unique(y_true)) >= 2
    predictions = (probabilities >= 0.5).astype(int)
    return {
        "test_pr_auc": _pr_auc(y_true, probabilities),
        "test_roc_auc": float(roc_auc_score(y_true, probabilities)) if both_classes else 0.0,
        "test_precision": float(precision_score(y_true, predictions, zero_division=0)) if both_classes else 0.0,
        "test_recall": float(recall_score(y_true, predictions, zero_division=0)) if both_classes else 0.0,
        "test_f1": float(f1_score(y_true, predictions, zero_division=0)) if both_classes else 0.0,
        "test_brier_score": float(brier_score_loss(y_true, probabilities)),
    }


def _train() -> dict[str, Any]:
    frame = _build_training_frame()
    train, validation, test = _split_by_transaction(frame)
    x_train, y_train = train[list(FEATURES)], train["recovered"]
    x_validation, y_validation = validation[list(FEATURES)], validation["recovered"]
    x_test, y_test = test[list(FEATURES)], test["recovered"]

    logistic = _build_pipeline(LogisticRegression(max_iter=1000, random_state=42), scale_numeric=True)
    gbt = _build_pipeline(HistGradientBoostingClassifier(max_iter=150, random_state=42), scale_numeric=False)
    logistic.fit(x_train, y_train)
    gbt.fit(x_train, y_train)

    logistic_validation_pr_auc = _pr_auc(y_validation, logistic.predict_proba(x_validation)[:, 1])
    gbt_validation_pr_auc = _pr_auc(y_validation, gbt.predict_proba(x_validation)[:, 1])
    if gbt_validation_pr_auc > logistic_validation_pr_auc:
        selected = gbt
        model_version = "gbt-recovery-v1"
    else:
        selected = logistic
        model_version = "logreg-recovery-v1"

    metrics = _test_metrics(y_test, selected.predict_proba(x_test)[:, 1])
    metrics["validation_pr_auc"] = float(gbt_validation_pr_auc if selected is gbt else logistic_validation_pr_auc)
    metrics["baseline_validation_pr_auc"] = float(logistic_validation_pr_auc)
    metrics["gbt_validation_pr_auc"] = float(gbt_validation_pr_auc)
    return {"model": selected, "model_version": model_version, "model_metrics": metrics}


def get_recovery_model() -> dict[str, Any]:
    """Return the process-cached trained model bundle."""
    global _MODEL_BUNDLE
    if _MODEL_BUNDLE is None:
        with _MODEL_LOCK:
            if _MODEL_BUNDLE is None:
                _MODEL_BUNDLE = _train()
    return _MODEL_BUNDLE


def predict_action_probabilities(transaction: dict[str, Any], customer_profile: dict[str, Any]) -> dict[str, Any]:
    """Predict recovery probability for each candidate action using observable inputs only."""
    bundle = get_recovery_model()
    rows = pd.DataFrame([_feature_row(transaction, customer_profile, action) for action in CANDIDATE_ACTIONS], columns=FEATURES)
    probabilities = bundle["model"].predict_proba(rows)[:, 1]
    return {
        "action_probabilities": {action: float(probability) for action, probability in zip(CANDIDATE_ACTIONS, probabilities)},
        "model_version": bundle["model_version"],
        "model_metrics": bundle["model_metrics"],
    }
