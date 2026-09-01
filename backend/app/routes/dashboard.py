"""Dashboard API endpoints."""

from fastapi import APIRouter

from app.services.workflows import run_secondchance_strategy


router = APIRouter(prefix="/api", tags=["Dashboard"])


@router.get("/dashboard")
def get_dashboard() -> dict:
    """Return summary metrics and the latest observable recovery cases."""
    transactions, decisions, metrics = run_secondchance_strategy()
    decisions_by_id = {
        decision["transaction_id"]: decision for decision in decisions
    }
    latest_transactions = sorted(
        transactions,
        key=lambda transaction: transaction["transaction_timestamp"],
        reverse=True,
    )[:10]
    recent_cases = [
        {
            "transaction_id": transaction["transaction_id"],
            "amount": transaction["amount"],
            "failure_reason": transaction["failure_reason"],
            "recommended_action": decisions_by_id[transaction["transaction_id"]]["recommended_action"],
            "recovery_probability": decisions_by_id[transaction["transaction_id"]]["recovery_probability"],
            "confidence": decisions_by_id[transaction["transaction_id"]]["confidence"],
            "transaction_timestamp": transaction["transaction_timestamp"],
        }
        for transaction in latest_transactions
    ]
    return {
        "summary": {
            "total_cases": metrics["total_transactions"],
            "revenue_at_risk": metrics["total_revenue_at_risk"],
            "recovered_revenue": metrics["recovered_revenue"],
            "revenue_recovery_rate": metrics["revenue_recovery_rate"],
            "recovery_rate": metrics["recovery_rate"],
            "total_friction_cost": metrics["total_friction_cost"],
        },
        "action_distribution": metrics["action_distribution"],
        "recent_cases": recent_cases,
    }
