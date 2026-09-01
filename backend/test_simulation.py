"""Run the guarded baseline strategy against the local simulation dataset."""

from app.services.baseline import get_baseline_decision
from app.services.data_generator import load_dataset
from app.services.guardrails import apply_guardrails
from app.services.metrics import calculate_metrics
from app.services.simulator import simulate_strategy


def main() -> None:
    """Run the baseline recovery simulation and print its summary metrics."""
    transactions, customer_profiles, simulation_truth = load_dataset()
    customers = {customer["customer_id"]: customer for customer in customer_profiles}

    decisions = []
    for transaction in transactions:
        customer = customers[transaction["customer_id"]]
        decision = get_baseline_decision(transaction, customer)
        guardrail_result = apply_guardrails(
            transaction, customer, decision["recommended_action"]
        )
        decision["recommended_action"] = guardrail_result["final_action"]
        decisions.append(decision)

    results = simulate_strategy(transactions, customers, decisions, simulation_truth)
    metrics = calculate_metrics(results)

    print("SecondChance Simulation Test")
    print(f"Total transactions: {metrics['total_transactions']}")
    print(f"Recovered transactions: {metrics['recovered_transactions']}")
    print(f"Recovery rate: {metrics['recovery_rate']}%")
    print(f"Total revenue at risk: {metrics['total_revenue_at_risk']}")
    print(f"Recovered revenue: {metrics['recovered_revenue']}")
    print(f"Revenue recovery rate: {metrics['revenue_recovery_rate']}%")
    print(f"Total friction cost: {metrics['total_friction_cost']}")
    print(
        "Average friction per transaction: "
        f"{metrics['average_friction_per_transaction']}"
    )
    print(f"Action distribution: {metrics['action_distribution']}")


if __name__ == "__main__":
    main()
