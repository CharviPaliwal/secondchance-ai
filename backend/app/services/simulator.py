"""Deterministic recovery simulation using simulator-only hidden truth."""

from __future__ import annotations

import hashlib
import random
from typing import Any


FRICTION_COSTS = {
    "RETRY_NOW": 1.0,
    "RETRY_LATER": 0.5,
    "SEND_REMINDER": 1.5,
    "UPDATE_PAYMENT_METHOD": 2.0,
    "ESCALATE_TO_HUMAN": 3.0,
    "STOP_RECOVERY": 0.0,
}


def _action_value(action: Any) -> str:
    return getattr(action, "value", action)


def simulate_action(
    transaction: dict[str, Any], action: str, truth: dict[str, Any]
) -> dict[str, Any]:
    """Evaluate one action with a stable action-specific pseudo-random draw."""
    action_value = _action_value(action)
    probabilities = truth.get("action_success_probabilities", {})
    probability = float(probabilities.get(action_value, 0.0))
    action_offset = int(hashlib.sha256(action_value.encode("utf-8")).hexdigest(), 16)
    combined_seed = int(truth.get("simulation_seed", 0)) + action_offset
    success = random.Random(combined_seed).random() < probability

    return {
        "transaction_id": transaction.get("transaction_id"),
        "action": action_value,
        "success": success,
        "success_probability": probability,
        "amount": float(transaction.get("amount", 0)),
        "recovered_amount": float(transaction.get("amount", 0)) if success else 0.0,
        "friction_cost": FRICTION_COSTS.get(action_value, 0.0),
    }


def simulate_strategy(
    transactions: list[dict[str, Any]],
    customers: dict[str, dict[str, Any]],
    decisions: list[dict[str, Any]],
    simulation_truth: list[dict[str, Any]] | dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    """Simulate one chosen action for each transaction.

    Customer data is accepted for a consistent strategy interface but is not
    needed once decisions have been made.
    """
    del customers
    decisions_by_id = {
        decision.get("transaction_id"): decision
        for decision in decisions
        if decision.get("transaction_id") is not None
    }
    truth_by_id = (
        simulation_truth
        if isinstance(simulation_truth, dict)
        else {item.get("transaction_id"): item for item in simulation_truth}
    )

    results: list[dict[str, Any]] = []
    for transaction in transactions:
        transaction_id = transaction.get("transaction_id")
        decision = decisions_by_id.get(transaction_id, {})
        action = decision.get("final_action", decision.get("recommended_action", "STOP_RECOVERY"))
        truth = truth_by_id.get(transaction_id, {})
        results.append(simulate_action(transaction, action, truth))
    return results
