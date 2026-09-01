"""Deterministic safety and customer-friction guardrails."""

from typing import Any


def apply_guardrails(
    transaction: dict[str, Any], customer: dict[str, Any], proposed_action: str
) -> dict[str, Any]:
    """Approve or safely override a proposed recovery action."""
    action = getattr(proposed_action, "value", proposed_action)
    reasons: list[str] = []

    if action in {"RETRY_NOW", "RETRY_LATER"} and transaction.get("attempt_count", 0) >= 3:
        action = "STOP_RECOVERY"
        reasons.append("Maximum safe retry threshold reached")
    elif action == "SEND_REMINDER" and customer.get("contacts_last_7_days", 0) >= 3:
        action = "STOP_RECOVERY"
        reasons.append("Customer contact frequency limit reached")
    elif action == "RETRY_NOW" and transaction.get("amount", 0) >= 30000:
        action = "ESCALATE_TO_HUMAN"
        reasons.append("High-value transaction requires controlled handling")
    elif action == "RETRY_NOW" and customer.get("payment_success_rate", 0) < 0.30:
        action = "STOP_RECOVERY"
        reasons.append("Low historical payment reliability")

    return {
        "original_action": getattr(proposed_action, "value", proposed_action),
        "final_action": action,
        "was_modified": bool(reasons),
        "guardrail_reasons": reasons,
    }
