"""Generic rule-based recovery recommendations."""

from typing import Any


_DELAYS = {
    "RETRY_NOW": 0,
    "RETRY_LATER": 1440,
    "SEND_REMINDER": None,
    "UPDATE_PAYMENT_METHOD": None,
    "ESCALATE_TO_HUMAN": None,
    "STOP_RECOVERY": None,
}


def get_baseline_decision(transaction: dict[str, Any], customer: dict[str, Any]) -> dict[str, Any]:
    """Return a generic, non-personalized recovery recommendation.

    ``customer`` is accepted to retain a common interface with future strategies;
    the intentionally simple baseline does not use it.
    """
    del customer
    attempt_count = transaction.get("attempt_count", 0)
    failure_reason = transaction.get("failure_reason")
    amount = transaction.get("amount", 0)

    if attempt_count >= 4:
        action, reason = "STOP_RECOVERY", "Attempt limit reached"
    elif failure_reason in {"BANK_TIMEOUT", "NETWORK_ERROR"}:
        action, reason = "RETRY_NOW", "Temporary payment processing failure"
    elif failure_reason == "INSUFFICIENT_FUNDS":
        action, reason = "SEND_REMINDER", "Insufficient funds may resolve later"
    elif failure_reason in {"CARD_EXPIRED", "MANDATE_FAILED"}:
        action, reason = "UPDATE_PAYMENT_METHOD", "Payment method needs attention"
    elif amount >= 20000:
        action, reason = "ESCALATE_TO_HUMAN", "High-value transaction"
    else:
        action, reason = "RETRY_LATER", "Standard delayed retry workflow"

    return {
        "transaction_id": transaction.get("transaction_id"),
        "recommended_action": action,
        "recommended_delay_minutes": _DELAYS[action],
        "strategy": "baseline",
        "reasoning": [reason],
    }
