"""Compare the guarded baseline and SecondChance recovery strategies."""

from app.services.baseline import get_baseline_decision
from app.services.data_generator import load_dataset
from app.services.guardrails import apply_guardrails
from app.services.intelligence import analyze_transaction
from app.services.metrics import calculate_metrics
from app.services.simulator import simulate_strategy


def _apply_guardrails(transaction: dict, customer: dict, decision: dict) -> dict:
    """Apply safety controls while retaining all original decision fields."""
    guardrail_result = apply_guardrails(
        transaction, customer, decision["recommended_action"]
    )
    decision["recommended_action"] = guardrail_result["final_action"]
    return decision


def _print_metrics(label: str, metrics: dict) -> None:
    print(label)
    print(f"Recovery Rate: {metrics['recovery_rate']}%")
    print(f"Recovered Revenue: ₹{metrics['recovered_revenue']:,.2f}")
    print(f"Revenue Recovery Rate: {metrics['revenue_recovery_rate']}%")
    print(f"Total Friction Cost: {metrics['total_friction_cost']:.2f}")
    print()


def main() -> None:
    """Run both strategies and print an observable-data comparison."""
    transactions, customer_profiles, simulation_truth = load_dataset()
    customers = {customer["customer_id"]: customer for customer in customer_profiles}
    truth_by_transaction = {
        truth["transaction_id"]: truth for truth in simulation_truth
    }

    baseline_decisions = [
        _apply_guardrails(
            transaction,
            customers[transaction["customer_id"]],
            get_baseline_decision(transaction, customers[transaction["customer_id"]]),
        )
        for transaction in transactions
    ]
    baseline_results = simulate_strategy(
        transactions, customers, baseline_decisions, truth_by_transaction
    )
    baseline_metrics = calculate_metrics(baseline_results)

    intelligence_decisions = [
        _apply_guardrails(
            transaction,
            customers[transaction["customer_id"]],
            analyze_transaction(transaction, customers[transaction["customer_id"]]),
        )
        for transaction in transactions
    ]
    intelligence_results = simulate_strategy(
        transactions, customers, intelligence_decisions, truth_by_transaction
    )
    intelligence_metrics = calculate_metrics(intelligence_results)

    additional_revenue = (
        intelligence_metrics["recovered_revenue"] - baseline_metrics["recovered_revenue"]
    )
    revenue_rate_improvement = (
        intelligence_metrics["revenue_recovery_rate"]
        - baseline_metrics["revenue_recovery_rate"]
    )
    recovery_rate_improvement = (
        intelligence_metrics["recovery_rate"] - baseline_metrics["recovery_rate"]
    )
    friction_difference = (
        intelligence_metrics["total_friction_cost"]
        - baseline_metrics["total_friction_cost"]
    )

    print("=" * 50)
    print("SECONDCHANCE VS BASELINE")
    print("=" * 50)
    _print_metrics("BASELINE", baseline_metrics)
    _print_metrics("SECONDCHANCE", intelligence_metrics)
    print("IMPROVEMENT")
    print(f"Additional Recovered Revenue: ₹{additional_revenue:,.2f}")
    print(f"Revenue Recovery Improvement: {revenue_rate_improvement:.2f} percentage points")
    print(f"Recovery Rate Improvement: {recovery_rate_improvement:.2f} percentage points")
    print(f"Friction Difference: {friction_difference:.2f}")
    print()
    print(f"SecondChance Action Distribution: {intelligence_metrics['action_distribution']}")
    print()
    print("SAMPLE INTELLIGENT DECISIONS")

    for transaction, decision in zip(transactions[:5], intelligence_decisions):
        print(f"Transaction ID: {decision['transaction_id']}")
        print(f"Amount: ₹{transaction['amount']:,.2f}")
        print(f"Failure Reason: {transaction['failure_reason']}")
        print(f"Diagnosis: {decision['diagnosis']}")
        print(f"Recommended Action: {decision['recommended_action']}")
        print(f"Recovery Probability: {decision['recovery_probability']:.0%}")
        print(f"Confidence: {decision['confidence']:.0%}")
        print("Reasoning:")
        for reason in decision["reasoning"]:
            print(f"- {reason}")
        print()


if __name__ == "__main__":
    main()
