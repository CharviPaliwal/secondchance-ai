"""Explainable, observable-data-only recovery decision engine."""

from __future__ import annotations

from typing import Any

from app.ml.model import metadata as model_metadata
from app.ml.model import predict_action_probabilities


ACTIONS = (
    "RETRY_NOW",
    "RETRY_LATER",
    "SEND_REMINDER",
    "UPDATE_PAYMENT_METHOD",
    "ESCALATE_TO_HUMAN",
    "STOP_RECOVERY",
)
TIE_BREAK_PRIORITY = (
    "UPDATE_PAYMENT_METHOD",
    "RETRY_LATER",
    "SEND_REMINDER",
    "ESCALATE_TO_HUMAN",
    "RETRY_NOW",
    "STOP_RECOVERY",
)
FRICTION_COSTS = {
    "RETRY_NOW": 1.0,
    "RETRY_LATER": 0.5,
    "SEND_REMINDER": 1.5,
    "UPDATE_PAYMENT_METHOD": 2.0,
    "ESCALATE_TO_HUMAN": 3.0,
    "STOP_RECOVERY": 0.0,
}
FRICTION_PENALTY_PER_COST = 300

_FAILURE_SCORES = {
    "BANK_TIMEOUT": {"RETRY_NOW": 30, "RETRY_LATER": 20},
    "NETWORK_ERROR": {"RETRY_NOW": 25, "RETRY_LATER": 20},
    "INSUFFICIENT_FUNDS": {"RETRY_LATER": 30, "SEND_REMINDER": 10},
    "USER_ABANDONED": {"SEND_REMINDER": 30, "RETRY_LATER": 10},
    "PAYMENT_DECLINED": {
        "SEND_REMINDER": 15,
        "UPDATE_PAYMENT_METHOD": 15,
        "ESCALATE_TO_HUMAN": 5,
    },
    "CARD_EXPIRED": {"UPDATE_PAYMENT_METHOD": 40},
    "MANDATE_FAILED": {"UPDATE_PAYMENT_METHOD": 35, "SEND_REMINDER": 10},
}

_DIAGNOSES = {
    "BANK_TIMEOUT": "Likely temporary payment infrastructure failure",
    "NETWORK_ERROR": "Likely transient network failure",
    "INSUFFICIENT_FUNDS": "Likely temporary liquidity constraint",
    "USER_ABANDONED": "Checkout abandonment with potential for re-engagement",
    "CARD_EXPIRED": "Stored payment method likely requires update",
    "MANDATE_FAILED": "Recurring payment mandate requires customer intervention",
    "PAYMENT_DECLINED": "Payment declined; recovery path requires customer-aware intervention",
}


def _add_scores(scores: dict[str, int], adjustments: dict[str, int]) -> None:
    for action, adjustment in adjustments.items():
        scores[action] += adjustment


def _score_actions(transaction: dict[str, Any], customer: dict[str, Any]) -> dict[str, int]:
    """Score each candidate action from observable transaction signals."""
    scores = {action: 0 for action in ACTIONS}
    payment_success_rate = float(customer.get("payment_success_rate", 0))
    previous_recovery_rate = float(customer.get("previous_recovery_success_rate", 0))
    contacts = int(customer.get("contacts_last_7_days", 0))
    attempts = int(transaction.get("attempt_count", 0))
    amount = float(transaction.get("amount", 0))

    if payment_success_rate >= 0.90:
        _add_scores(scores, {"RETRY_NOW": 25, "RETRY_LATER": 30})
    elif payment_success_rate >= 0.75:
        _add_scores(scores, {"RETRY_NOW": 15, "RETRY_LATER": 20, "SEND_REMINDER": 5})
    elif payment_success_rate >= 0.50:
        _add_scores(scores, {"RETRY_LATER": 10, "SEND_REMINDER": 15, "UPDATE_PAYMENT_METHOD": 10})
    else:
        _add_scores(scores, {"STOP_RECOVERY": 20, "SEND_REMINDER": 5, "ESCALATE_TO_HUMAN": 5})

    _add_scores(scores, _FAILURE_SCORES.get(transaction.get("failure_reason"), {}))

    if attempts == 1:
        _add_scores(scores, {"RETRY_NOW": 10, "RETRY_LATER": 10})
    elif attempts == 2:
        _add_scores(scores, {"RETRY_LATER": 15, "SEND_REMINDER": 10})
    elif attempts >= 3:
        _add_scores(scores, {"STOP_RECOVERY": 30, "ESCALATE_TO_HUMAN": 5})

    if previous_recovery_rate >= 0.75:
        _add_scores(scores, {"RETRY_LATER": 20, "RETRY_NOW": 10})
    elif previous_recovery_rate >= 0.40:
        _add_scores(scores, {"SEND_REMINDER": 10, "RETRY_LATER": 10})
    elif previous_recovery_rate < 0.20:
        _add_scores(scores, {"STOP_RECOVERY": 15})

    if contacts == 0:
        _add_scores(scores, {"SEND_REMINDER": 10})
    elif contacts >= 2:
        _add_scores(scores, {"STOP_RECOVERY": 15, "SEND_REMINDER": -20})

    if amount >= 30000:
        _add_scores(scores, {"ESCALATE_TO_HUMAN": 30})
    elif amount >= 15000:
        _add_scores(scores, {"ESCALATE_TO_HUMAN": 10})
    if amount >= 20000:
        _add_scores(scores, {"ESCALATE_TO_HUMAN": 20})
    return scores


def _estimated_probabilities(scores: dict[str, int]) -> dict[str, float]:
    """Convert transparent raw scores into bounded action success estimates."""
    return {
        action: min(0.95, max(0.02, score / 100))
        for action, score in scores.items()
    }


def _expected_action_values(
    amount: float, probabilities: dict[str, float]
) -> dict[str, float]:
    """Estimate recovered INR after the fixed action-friction penalty."""
    return {
        action: 0.0
        if action == "STOP_RECOVERY"
        else amount * probability - FRICTION_COSTS[action] * FRICTION_PENALTY_PER_COST
        for action, probability in probabilities.items()
    }


def _select_action(
    scores: dict[str, int],
    probabilities: dict[str, float],
    action_values: dict[str, float],
    transaction: dict[str, Any],
    customer: dict[str, Any],
) -> tuple[str, int, int]:
    """Select by expected value, with deterministic safety and value overrides."""
    priority = {action: index for index, action in enumerate(TIE_BREAK_PRIORITY)}
    ranked_by_value = sorted(
        action_values, key=lambda action: (-action_values[action], priority[action])
    )
    selected_action = ranked_by_value[0]

    amount = float(transaction.get("amount", 0))
    attempts = int(transaction.get("attempt_count", 0))
    recovery_rate = float(customer.get("previous_recovery_success_rate", 0))
    contacts = int(customer.get("contacts_last_7_days", 0))
    payment_success_rate = float(customer.get("payment_success_rate", 0))
    safety_stop = attempts >= 3 and (
        recovery_rate < 0.25 or contacts >= 3 or payment_success_rate < 0.40
    )

    non_stop_probabilities = [
        probability for action, probability in probabilities.items() if action != "STOP_RECOVERY"
    ]
    if amount >= 30000 and max(non_stop_probabilities) < 0.30 and contacts < 3:
        selected_action = "ESCALATE_TO_HUMAN"
    if safety_stop:
        selected_action = "STOP_RECOVERY"

    ranked_by_score = sorted(scores, key=lambda action: (-scores[action], priority[action]))
    return selected_action, scores[ranked_by_score[0]], scores[ranked_by_score[1]]


def _diagnosis(transaction: dict[str, Any], customer: dict[str, Any]) -> str:
    diagnosis = _DIAGNOSES.get(
        transaction.get("failure_reason"), "Payment failure requires recovery assessment"
    )
    if int(transaction.get("attempt_count", 0)) >= 3:
        diagnosis += ". Repeated recovery attempts indicate elevated recovery fatigue"
    if int(customer.get("contacts_last_7_days", 0)) >= 2:
        diagnosis += ". Recent customer contact volume increases friction risk"
    return diagnosis


def _reasoning(transaction: dict[str, Any], customer: dict[str, Any]) -> list[str]:
    """Build concise statements tied directly to observed input values."""
    payment_success_rate = float(customer.get("payment_success_rate", 0))
    previous_recovery_rate = float(customer.get("previous_recovery_success_rate", 0))
    attempts = int(transaction.get("attempt_count", 0))
    contacts = int(customer.get("contacts_last_7_days", 0))
    amount = float(transaction.get("amount", 0))
    statements = [
        f"Historical payment success rate is {payment_success_rate:.0%}",
        f"Failure reason {transaction.get('failure_reason', 'UNKNOWN')} guides the recovery path",
        f"Customer has {attempts} recovery attempt{'s' if attempts != 1 else ''} so far",
        f"Previous recovery success rate is {previous_recovery_rate:.0%}",
        f"Customer has been contacted {contacts} time{'s' if contacts != 1 else ''} in the last 7 days",
    ]
    if amount >= 20000:
        statements.append(
            f"Transaction value is ₹{amount:,.0f}, so recovery decisions are prioritized by expected revenue impact"
        )
    elif amount >= 15000:
        statements.append(f"Transaction value ₹{amount:,.0f} warrants controlled handling")
    return statements[:6]


def _reason_codes(transaction: dict[str, Any], customer: dict[str, Any]) -> list[str]:
    """Structured, observable reason codes for UI and audit consumers."""
    codes = []
    if float(customer.get("payment_success_rate", 0)) >= .75:
        codes.append("HIGH_SUCCESS_HISTORY")
    if int(transaction.get("attempt_count", 0)) <= 1:
        codes.append("LOW_ATTEMPT_COUNT")
    if transaction.get("failure_reason") in {"BANK_TIMEOUT", "NETWORK_ERROR"}:
        codes.append("TEMPORARY_PAYMENT_FAILURE")
    if int(customer.get("contacts_last_7_days", 0)) >= 2:
        codes.append("CUSTOMER_CONTACT_FATIGUE")
    if float(transaction.get("amount", 0)) >= 15_000:
        codes.append("HIGH_TRANSACTION_VALUE")
    if float(customer.get("previous_recovery_success_rate", 0)) < .2:
        codes.append("LOW_RECOVERY_PROBABILITY")
    if int(transaction.get("attempt_count", 0)) >= 3:
        codes.append("REPEATED_FAILURE")
    if transaction.get("failure_reason") in {"CARD_EXPIRED", "MANDATE_FAILED"}:
        codes.append("PAYMENT_METHOD_UPDATE_REQUIRED")
    return codes


def _priority_score(transaction: dict[str, Any], customer: dict[str, Any], probability: float) -> float:
    """Explainable expected-value priority, reduced by retry/contact fatigue."""
    amount = float(transaction.get("amount", 0))
    severity = {"CARD_EXPIRED": 1.25, "MANDATE_FAILED": 1.2, "PAYMENT_DECLINED": 1.1}.get(transaction.get("failure_reason"), 1.0)
    attempts = int(transaction.get("attempt_count", 0))
    contacts = int(customer.get("contacts_last_7_days", 0))
    fatigue = max(.35, 1 - .12 * max(attempts - 1, 0) - .10 * contacts)
    return amount * probability * severity * fatigue


def _priority_level(score: float) -> str:
    return "CRITICAL" if score >= 20_000 else "HIGH" if score >= 9_000 else "MEDIUM" if score >= 3_000 else "LOW"


def analyze_transaction(
    transaction: dict[str, Any], customer: dict[str, Any], model_probabilities: dict[str, float] | None = None
) -> dict[str, Any]:
    """Analyze a failed payment and return an explainable recovery decision."""
    fallback_scores = _score_actions(transaction, customer)
    inferred_probabilities = model_probabilities or predict_action_probabilities(transaction, customer)
    estimated_action_probabilities = inferred_probabilities or _estimated_probabilities(fallback_scores)
    # Scores are presentation-friendly probability points; expected value remains
    # the canonical decision criterion below.
    action_scores = {
        action: round(probability * 100, 2)
        for action, probability in estimated_action_probabilities.items()
    }
    amount = float(transaction.get("amount", 0))
    expected_action_values = _expected_action_values(amount, estimated_action_probabilities)
    action, highest_score, second_highest_score = _select_action(
        action_scores,
        estimated_action_probabilities,
        expected_action_values,
        transaction,
        customer,
    )
    recovery_probability = estimated_action_probabilities[action]
    ranked_probabilities = sorted(estimated_action_probabilities.values(), reverse=True)
    probability_margin = ranked_probabilities[0] - ranked_probabilities[1]
    # Confidence is derived from the model/fallback probability separation, not invented.
    confidence = min(0.95, max(0.35, 0.45 + probability_margin))
    delay = 0 if action == "RETRY_NOW" else 1440 if action == "RETRY_LATER" and transaction.get("failure_reason") == "INSUFFICIENT_FUNDS" else 60 if action == "RETRY_LATER" else None

    return {
        "transaction_id": str(transaction.get("transaction_id", "")),
        "diagnosis": _diagnosis(transaction, customer),
        "recovery_probability": round(recovery_probability, 2),
        "recommended_action": action,
        "recommended_delay_minutes": delay,
        "confidence": round(confidence, 2),
        "reasoning": _reasoning(transaction, customer),
        "action_scores": action_scores,
        "estimated_action_probabilities": {
            candidate: round(probability, 2)
            for candidate, probability in estimated_action_probabilities.items()
        },
        "expected_action_values": {
            candidate: round(value, 2)
            for candidate, value in expected_action_values.items()
        },
        "reason_codes": _reason_codes(transaction, customer),
        "model": model_metadata(),
        "priority_score": round(_priority_score(transaction, customer, recovery_probability), 2),
        "priority_level": _priority_level(_priority_score(transaction, customer, recovery_probability)),
    }
