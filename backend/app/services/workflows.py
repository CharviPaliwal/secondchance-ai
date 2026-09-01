"""Internal orchestration helpers shared by the API routes."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from app.services.baseline import get_baseline_decision
from app.services.data_generator import load_dataset
from app.services.guardrails import apply_guardrails
from app.services.intelligence import analyze_transaction
from app.services.metrics import calculate_metrics
from app.services.simulator import simulate_strategy


@lru_cache(maxsize=1)
def get_dataset() -> tuple[
    list[dict[str, Any]],
    dict[str, dict[str, Any]],
    dict[str, dict[str, Any]],
]:
    """Load local data once and construct internal lookup dictionaries."""
    transactions, customer_profiles, simulation_truth = load_dataset()
    customers = {customer["customer_id"]: customer for customer in customer_profiles}
    truth = {item["transaction_id"]: item for item in simulation_truth}
    return transactions, customers, truth


def secondchance_decision(
    transaction: dict[str, Any], customer: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Analyze a case, enforce guardrails, and retain the full internal decision."""
    analysis = analyze_transaction(transaction, customer)
    guardrails = apply_guardrails(
        transaction, customer, analysis["recommended_action"]
    )
    decision = {**analysis, "recommended_action": guardrails["final_action"]}
    return analysis, guardrails, decision


def _baseline_decision(
    transaction: dict[str, Any], customer: dict[str, Any]
) -> dict[str, Any]:
    decision = get_baseline_decision(transaction, customer)
    guardrails = apply_guardrails(
        transaction, customer, decision["recommended_action"]
    )
    return {**decision, "recommended_action": guardrails["final_action"]}


def run_secondchance_strategy() -> tuple[
    list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]
]:
    """Run the internal SecondChance simulation and aggregate its metrics."""
    transactions, customers, truth = get_dataset()
    decisions = [
        secondchance_decision(transaction, customers[transaction["customer_id"]])[2]
        for transaction in transactions
    ]
    results = simulate_strategy(transactions, customers, decisions, truth)
    return transactions, decisions, calculate_metrics(results)


def run_comparison() -> dict[str, Any]:
    """Run guarded baseline and SecondChance strategies for internal comparison."""
    transactions, customers, truth = get_dataset()
    baseline_decisions = [
        _baseline_decision(transaction, customers[transaction["customer_id"]])
        for transaction in transactions
    ]
    secondchance_decisions = [
        secondchance_decision(transaction, customers[transaction["customer_id"]])[2]
        for transaction in transactions
    ]
    baseline_metrics = calculate_metrics(
        simulate_strategy(transactions, customers, baseline_decisions, truth)
    )
    secondchance_metrics = calculate_metrics(
        simulate_strategy(transactions, customers, secondchance_decisions, truth)
    )
    return {
        "baseline": baseline_metrics,
        "secondchance": secondchance_metrics,
        "improvement": {
            "additional_recovered_revenue": round(
                secondchance_metrics["recovered_revenue"]
                - baseline_metrics["recovered_revenue"],
                2,
            ),
            "revenue_recovery_rate_improvement": round(
                secondchance_metrics["revenue_recovery_rate"]
                - baseline_metrics["revenue_recovery_rate"],
                2,
            ),
            "recovery_rate_improvement": round(
                secondchance_metrics["recovery_rate"]
                - baseline_metrics["recovery_rate"],
                2,
            ),
            "friction_difference": round(
                secondchance_metrics["total_friction_cost"]
                - baseline_metrics["total_friction_cost"],
                2,
            ),
        },
    }
