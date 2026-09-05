"""Reproducibly train the observable, action-conditioned recovery model.

Run: ``python -m app.ml.train`` from the backend directory.
"""
from __future__ import annotations

import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.ml.features import FEATURE_VERSION, build_features
from app.ml.model import CANDIDATE_ACTIONS, MODEL_PATH, MODEL_VERSION

SEED = 20260901
TRAINING_ROWS = 24_000


def _outcome_probability(transaction: dict, customer: dict, action: str) -> float:
    """Internal synthetic historical outcome generator; uses observable signals only."""
    reason = transaction["failure_reason"]
    attempts, contacts = transaction["attempt_count"], customer["contacts_last_7_days"]
    base = .12 + .42 * customer["payment_success_rate"] + .22 * customer["previous_recovery_success_rate"]
    preferences = {
        "BANK_TIMEOUT": {"RETRY_NOW": .24, "RETRY_LATER": .31}, "NETWORK_ERROR": {"RETRY_NOW": .21, "RETRY_LATER": .27},
        "INSUFFICIENT_FUNDS": {"RETRY_LATER": .32, "SEND_REMINDER": .10}, "USER_ABANDONED": {"SEND_REMINDER": .30, "RETRY_LATER": .10},
        "CARD_EXPIRED": {"UPDATE_PAYMENT_METHOD": .42}, "MANDATE_FAILED": {"UPDATE_PAYMENT_METHOD": .38, "SEND_REMINDER": .10},
        "PAYMENT_DECLINED": {"SEND_REMINDER": .13, "UPDATE_PAYMENT_METHOD": .14, "ESCALATE_TO_HUMAN": .08},
    }
    probability = base + preferences.get(reason, {}).get(action, -.22) - .10 * max(attempts - 1, 0) - .08 * contacts
    if action == "ESCALATE_TO_HUMAN" and transaction["amount"] >= 15_000: probability += .18
    if action == "STOP_RECOVERY": return .01
    return min(.96, max(.01, probability))


def _examples(count: int = TRAINING_ROWS) -> tuple[list[dict], list[int]]:
    rng = random.Random(SEED)
    reasons = ["BANK_TIMEOUT", "NETWORK_ERROR", "INSUFFICIENT_FUNDS", "USER_ABANDED", "PAYMENT_DECLINED", "CARD_EXPIRED", "MANDATE_FAILED"]
    # Correct misspelling in sampling source while preserving a simple visible schema.
    reasons[3] = "USER_ABANDONED"
    methods = ["CARD", "UPI", "NETBANKING", "WALLET"]
    categories = ["E_COMMERCE", "SAAS", "SUBSCRIPTION", "MARKETPLACE"]
    rows, labels = [], []
    for index in range(count):
        amount = round(rng.uniform(199, 50_000), 2)
        transaction = {"transaction_id": f"HIST_{index}", "amount": amount, "attempt_count": rng.randint(1, 4), "failure_reason": rng.choice(reasons), "payment_method": rng.choice(methods), "merchant_category": rng.choice(categories), "transaction_timestamp": (datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(hours=rng.randrange(8_760))).isoformat()}
        customer = {"payment_success_rate": round(rng.uniform(.15, .99), 2), "previous_recovery_success_rate": round(rng.uniform(0, .95), 2), "contacts_last_7_days": rng.randint(0, 4), "average_transaction_amount": round(amount * rng.uniform(.5, 1.5), 2)}
        action = rng.choice(CANDIDATE_ACTIONS)
        rows.append(build_features(transaction, customer, action))
        labels.append(int(rng.random() < _outcome_probability(transaction, customer, action)))
    return rows, labels


def main() -> None:
    import joblib
    from sklearn.compose import ColumnTransformer
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.feature_extraction import DictVectorizer
    from sklearn.metrics import accuracy_score, f1_score
    from sklearn.model_selection import train_test_split
    from sklearn.pipeline import Pipeline

    rows, labels = _examples()
    train_rows, test_rows, train_y, test_y = train_test_split(rows, labels, test_size=.2, random_state=SEED, stratify=labels)
    pipeline = Pipeline([("features", DictVectorizer(sparse=True)), ("model", RandomForestClassifier(n_estimators=180, min_samples_leaf=8, n_jobs=-1, random_state=SEED, class_weight="balanced"))])
    pipeline.fit(train_rows, train_y)
    prediction = pipeline.predict(test_rows)
    metrics = {"accuracy": round(float(accuracy_score(test_y, prediction)), 4), "macro_f1": round(float(f1_score(test_y, prediction, average="macro")), 4), "test_size": len(test_y)}
    artifact = {"pipeline": pipeline, "metadata": {"model_name": "RandomForest action-conditioned recovery classifier", "model_version": MODEL_VERSION, "training_dataset_size": len(rows), "training_seed": SEED, "feature_version": FEATURE_VERSION, "trained_at": "2026-09-05T00:00:00Z", "evaluation": metrics}}
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(artifact, MODEL_PATH)
    MODEL_PATH.with_suffix(".metrics.json").write_text(json.dumps(artifact["metadata"], indent=2), encoding="utf-8")
    print(json.dumps(artifact["metadata"], indent=2))


if __name__ == "__main__":
    main()
