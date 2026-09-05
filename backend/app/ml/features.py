"""Shared observable feature schema for recovery-model training and inference."""
from __future__ import annotations

import math
from datetime import datetime
from typing import Any

FEATURE_VERSION = "v1-observable-action-conditioned"


def build_features(transaction: dict[str, Any], customer: dict[str, Any], action: str) -> dict[str, float | int | str]:
    """Return deterministic, observable-only features for one candidate action."""
    amount = float(transaction.get("amount", 0))
    average_amount = max(float(customer.get("average_transaction_amount", amount or 1)), 1)
    timestamp = transaction.get("transaction_timestamp", "")
    try:
        moment = datetime.fromisoformat(str(timestamp).replace("Z", "+00:00"))
        hour, weekday = moment.hour, moment.weekday()
    except ValueError:
        hour, weekday = 12, 0
    return {
        "transaction_amount": amount,
        "log_transaction_amount": math.log1p(max(amount, 0)),
        "attempt_count": int(transaction.get("attempt_count", 0)),
        "payment_success_rate": float(customer.get("payment_success_rate", 0)),
        "previous_recovery_success_rate": float(customer.get("previous_recovery_success_rate", 0)),
        "contacts_last_7_days": int(customer.get("contacts_last_7_days", 0)),
        "amount_vs_customer_average": amount / average_amount,
        "hour_of_day": hour,
        "day_of_week": weekday,
        "failure_reason": str(transaction.get("failure_reason", "UNKNOWN")),
        "payment_method": str(transaction.get("payment_method", "UNKNOWN")),
        "merchant_category": str(transaction.get("merchant_category", "UNKNOWN")),
        "candidate_action": action,
    }
