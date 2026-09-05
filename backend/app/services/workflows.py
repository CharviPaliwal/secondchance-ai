"""Internal orchestration helpers shared by the API routes."""

from __future__ import annotations

from functools import lru_cache
from datetime import datetime, timezone
import logging
from threading import Lock
from typing import Any
from copy import deepcopy
import random
import time

from app.services.baseline import get_baseline_decision
from app.services.data_generator import load_dataset
from app.services.guardrails import apply_guardrails
from app.services.intelligence import analyze_transaction
from app.ml.model import predict_batch_action_probabilities
from app.services.metrics import calculate_metrics
from app.services.simulator import simulate_strategy

logger = logging.getLogger(__name__)


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


_decision_cache_lock = Lock()
_decision_cache: dict[str, tuple[dict[str, Any], dict[str, Any], dict[str, Any]]] | None = None
_run_sequence_lock = Lock()
_run_sequence = 0


def get_secondchance_decisions() -> dict[str, tuple[dict[str, Any], dict[str, Any], dict[str, Any]]]:
    """Compute static dataset decisions once per process, not once per endpoint."""
    global _decision_cache
    if _decision_cache is not None:
        return _decision_cache
    with _decision_cache_lock:
        if _decision_cache is not None:
            return _decision_cache
        transactions, customers, _ = get_dataset()
        cases = [(transaction, customers[transaction["customer_id"]]) for transaction in transactions]
        batch_probabilities = predict_batch_action_probabilities(cases)
        _decision_cache = {
            transaction["transaction_id"]: _decision_with_probabilities(
                transaction,
                customers[transaction["customer_id"]],
                batch_probabilities[index] if batch_probabilities else None,
            )
            for index, transaction in enumerate(transactions)
        }
        return _decision_cache


def _decision_with_probabilities(transaction: dict[str, Any], customer: dict[str, Any], probabilities: dict[str, float] | None) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    analysis = analyze_transaction(transaction, customer, model_probabilities=probabilities)
    guardrails = apply_guardrails(transaction, customer, analysis["recommended_action"])
    return analysis, guardrails, {**analysis, "recommended_action": guardrails["final_action"]}


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
    cached = get_secondchance_decisions()
    decisions = [cached[transaction["transaction_id"]][2] for transaction in transactions]
    results = simulate_strategy(transactions, customers, decisions, truth)
    return transactions, decisions, calculate_metrics(results)


@lru_cache(maxsize=1)
def _comparison_core() -> dict[str, Any]:
    """Run guarded baseline and SecondChance strategies for internal comparison."""
    transactions, customers, truth = get_dataset()
    baseline_decisions = [
        _baseline_decision(transaction, customers[transaction["customer_id"]])
        for transaction in transactions
    ]
    cached = get_secondchance_decisions()
    secondchance_decisions = [cached[transaction["transaction_id"]][2] for transaction in transactions]
    baseline_results = simulate_strategy(transactions, customers, baseline_decisions, truth)
    secondchance_results = simulate_strategy(transactions, customers, secondchance_decisions, truth)
    baseline_metrics = calculate_metrics(baseline_results)
    secondchance_metrics = calculate_metrics(secondchance_results)
    results_by_id = {result["transaction_id"]: result for result in secondchance_results}
    decision_trace = []
    for transaction in transactions[:8]:
        analysis, guardrails, decision = cached[transaction["transaction_id"]]
        result = results_by_id[transaction["transaction_id"]]
        decision_trace.append({
            "transaction_id": transaction["transaction_id"],
            "amount": transaction["amount"],
            "failure_reason": transaction["failure_reason"],
            "diagnosis": analysis["diagnosis"],
            "recommended_action": decision["recommended_action"],
            "guardrail": "PASS" if not guardrails["was_modified"] else "; ".join(guardrails["guardrail_reasons"]),
            "outcome": "RECOVERED" if result["success"] else "NOT_RECOVERED",
        })
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
        "decision_trace": decision_trace,
    }


def run_comparison(force: bool = False) -> dict[str, Any]:
    """Return cached deterministic simulation metrics with a request completion envelope."""
    if force:
        logger.info("[Simulation] request received; loading 500 transactions")
        _comparison_core.cache_clear()
        logger.info("[Simulation] running baseline and SecondChance policies")
    core = _comparison_core()
    response = {
        "status": "completed",
        "transaction_count": core["secondchance"]["total_transactions"],
        "completed_at": datetime.now(timezone.utc).isoformat(),
        **core,
    }
    if force:
        logger.info("[Simulation] completed recovery_rate=%s recovered_revenue=%s friction_cost=%s", response["secondchance"]["recovery_rate"], response["secondchance"]["recovered_revenue"], response["secondchance"]["total_friction_cost"])
    return response


def _scenario_cohort(transactions: list[dict[str, Any]], customers: dict[str, dict[str, Any]], scenario: str, seed: int) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    """Create a deterministic in-memory experiment cohort; source JSON is never modified."""
    cohort, cohort_customers = deepcopy(transactions), deepcopy(customers)
    rng = random.Random(seed)
    emphasis = {
        "network_disruption": ("BANK_TIMEOUT", "NETWORK_ERROR"),
        "insufficient_funds_spike": ("INSUFFICIENT_FUNDS",),
        "card_expiry_wave": ("CARD_EXPIRED", "MANDATE_FAILED"),
    }
    if scenario in emphasis:
        targets = emphasis[scenario]
        for transaction in cohort:
            if rng.random() < .42:
                transaction["failure_reason"] = rng.choice(targets)
                if scenario == "card_expiry_wave": transaction["payment_method"] = "CARD"
    elif scenario == "high_value_failures":
        for transaction in cohort:
            if rng.random() < .5:
                transaction["amount"] = round(float(transaction["amount"]) * rng.uniform(2.0, 3.5), 2)
                cohort_customers[transaction["customer_id"]]["average_transaction_amount"] = round(float(cohort_customers[transaction["customer_id"]]["average_transaction_amount"]) * 1.8, 2)
    return cohort, cohort_customers


def _dynamic_decisions(transactions: list[dict[str, Any]], customers: dict[str, dict[str, Any]]) -> list[tuple[dict[str, Any], dict[str, Any], dict[str, Any]]]:
    cases = [(transaction, customers[transaction["customer_id"]]) for transaction in transactions]
    probabilities = predict_batch_action_probabilities(cases)
    return [_decision_with_probabilities(transaction, customers[transaction["customer_id"]], probabilities[index] if probabilities else None) for index, transaction in enumerate(transactions)]


def run_experiment(scenario: str = "standard", seed: int = 2026) -> dict[str, Any]:
    """Run a seeded, scenario-specific real comparison over a derived cohort."""
    if scenario not in {"standard", "network_disruption", "insufficient_funds_spike", "card_expiry_wave", "high_value_failures"}:
        raise ValueError("Unknown simulation scenario")
    started = time.perf_counter()
    logger.info("[Simulation] Run started")
    logger.info("[Simulation] Scenario: %s", scenario)
    logger.info("[Simulation] Seed: %s", seed)
    transactions, customers, truth = get_dataset()
    cohort, cohort_customers = _scenario_cohort(transactions, customers, scenario, seed)
    logger.info("[Simulation] Transactions: %s", len(cohort))
    baseline_decisions = [_baseline_decision(transaction, cohort_customers[transaction["customer_id"]]) for transaction in cohort]
    logger.info("[Simulation] Baseline evaluated")
    secondchance = _dynamic_decisions(cohort, cohort_customers)
    secondchance_decisions = [decision[2] for decision in secondchance]
    logger.info("[Simulation] SecondChance evaluated")
    logger.info("[Simulation] Guardrails applied")
    baseline_results = simulate_strategy(cohort, cohort_customers, baseline_decisions, truth, run_seed=seed)
    secondchance_results = simulate_strategy(cohort, cohort_customers, secondchance_decisions, truth, run_seed=seed)
    logger.info("[Simulation] Outcomes simulated")
    baseline_metrics, secondchance_metrics = calculate_metrics(baseline_results), calculate_metrics(secondchance_results)
    logger.info("[Simulation] Metrics calculated")
    results_by_id = {result["transaction_id"]: result for result in secondchance_results}
    trace = [{"transaction_id": transaction["transaction_id"], "amount": transaction["amount"], "failure_reason": transaction["failure_reason"], "diagnosis": analysis["diagnosis"], "recommended_action": decision["recommended_action"], "recovery_probability": analysis["recovery_probability"], "guardrail": "PASS" if not guardrails["was_modified"] else "; ".join(guardrails["guardrail_reasons"]), "outcome": "RECOVERED" if results_by_id[transaction["transaction_id"]]["success"] else "NOT_RECOVERED"} for transaction, (analysis, guardrails, decision) in zip(cohort[:10], secondchance[:10])]
    # These are cumulative values from this run's actual outcomes, not a visual approximation.
    trajectory = []
    for index in range(1, 11):
        end = max(1, round(len(cohort) * index / 10))
        trajectory.append({
            "step": index,
            "baseline_recovered_revenue": round(sum(item["recovered_amount"] for item in baseline_results[:end]), 2),
            "secondchance_recovered_revenue": round(sum(item["recovered_amount"] for item in secondchance_results[:end]), 2),
        })
    with _run_sequence_lock:
        global _run_sequence
        _run_sequence += 1
        sequence = _run_sequence
    duration_ms = round((time.perf_counter() - started) * 1000)
    logger.info("[Simulation] Run completed")
    logger.info("[Simulation] Duration: %sms", duration_ms)
    return {"status": "completed", "transaction_count": len(cohort), "scenario": scenario, "run_seed": seed, "run_id": f"SIM-{seed}-{scenario[:3].upper()}-{sequence:03d}", "duration_ms": duration_ms, "completed_at": datetime.now(timezone.utc).isoformat(), "baseline": baseline_metrics, "secondchance": secondchance_metrics, "improvement": {"additional_recovered_revenue": round(secondchance_metrics["recovered_revenue"] - baseline_metrics["recovered_revenue"], 2), "revenue_recovery_rate_improvement": round(secondchance_metrics["revenue_recovery_rate"] - baseline_metrics["revenue_recovery_rate"], 2), "recovery_rate_improvement": round(secondchance_metrics["recovery_rate"] - baseline_metrics["recovery_rate"], 2), "friction_difference": round(secondchance_metrics["total_friction_cost"] - baseline_metrics["total_friction_cost"], 2)}, "action_distribution": secondchance_metrics["action_distribution"], "trajectory": trajectory, "decision_trace": trace, "activity_log": ["Loading transaction cohort", "Baseline evaluated", "SecondChance decisions evaluated", "Guardrails applied", "Outcomes simulated", "Metrics calculated"]}
