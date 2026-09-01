"""Aggregate recovery simulation metrics."""

from collections import Counter
from typing import Any


def calculate_metrics(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Calculate recovery, revenue, friction, and action-distribution metrics."""
    total_transactions = len(results)
    recovered_transactions = sum(bool(result.get("success")) for result in results)
    total_revenue_at_risk = sum(float(result.get("amount", result.get("revenue_at_risk", 0))) for result in results)
    recovered_revenue = sum(float(result.get("recovered_amount", 0)) for result in results)
    total_friction_cost = sum(float(result.get("friction_cost", 0)) for result in results)
    action_distribution = Counter(str(result.get("action", "STOP_RECOVERY")) for result in results)

    return {
        "total_transactions": total_transactions,
        "recovered_transactions": recovered_transactions,
        "recovery_rate": round(recovered_transactions / total_transactions * 100, 2) if total_transactions else 0.0,
        "total_revenue_at_risk": round(total_revenue_at_risk, 2),
        "recovered_revenue": round(recovered_revenue, 2),
        "revenue_recovery_rate": round(recovered_revenue / total_revenue_at_risk * 100, 2) if total_revenue_at_risk else 0.0,
        "total_friction_cost": round(total_friction_cost, 2),
        "average_friction_per_transaction": round(total_friction_cost / total_transactions, 2) if total_transactions else 0.0,
        "action_distribution": dict(action_distribution),
    }
