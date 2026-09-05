"""Observable transaction and intelligence endpoints."""

from collections import defaultdict
from functools import lru_cache
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.models.schemas import CustomerProfile, Transaction
from app.services.workflows import get_dataset, get_secondchance_decisions, secondchance_decision


router = APIRouter(prefix="/api", tags=["Transactions"])
intelligence_router = APIRouter(prefix="/api", tags=["Intelligence"])


class AnalyzeRequest(BaseModel):
    """Observable inputs accepted by the ad-hoc analysis endpoint."""

    transaction: Transaction
    customer_profile: CustomerProfile


def _public_analysis(analysis: dict[str, Any]) -> dict[str, Any]:
    """Return analysis fields intended for API consumers."""
    return {
        "diagnosis": analysis["diagnosis"],
        "recommended_action": analysis["recommended_action"],
        "recommended_delay_minutes": analysis["recommended_delay_minutes"],
        "recovery_probability": analysis["recovery_probability"],
        "confidence": analysis["confidence"],
        "reasoning": analysis["reasoning"],
        "reason_codes": analysis["reason_codes"],
        "action_scores": analysis["action_scores"],
        "estimated_action_probabilities": analysis["estimated_action_probabilities"],
        "expected_action_values": analysis["expected_action_values"],
        "model": analysis["model"],
        "priority_score": analysis["priority_score"],
        "priority_level": analysis["priority_level"],
    }


def _priority(transaction: dict[str, Any], analysis: dict[str, Any], customer: dict[str, Any]) -> str:
    """Rank by expected recoverable value, severity, retries, and contact fatigue."""
    if "priority_level" in analysis:
        return str(analysis["priority_level"])
    expected_value = float(transaction["amount"]) * float(analysis["recovery_probability"])
    severity = {"CARD_EXPIRED": 1.25, "MANDATE_FAILED": 1.2, "PAYMENT_DECLINED": 1.1}.get(transaction["failure_reason"], 1.0)
    fatigue = .65 if int(customer.get("contacts_last_7_days", 0)) >= 3 else .8 if int(transaction.get("attempt_count", 0)) >= 3 else 1.0
    score = expected_value * severity * fatigue
    return "CRITICAL" if score >= 20_000 else "HIGH" if score >= 9_000 else "MEDIUM" if score >= 3_000 else "LOW"


def _transaction_item(transaction: dict[str, Any], decision: dict[str, Any], analysis: dict[str, Any], customer: dict[str, Any]) -> dict[str, Any]:
    """Build the compact observable transaction response item."""
    return {
        "transaction_id": transaction["transaction_id"],
        "customer_id": transaction["customer_id"],
        "amount": transaction["amount"],
        "currency": transaction["currency"],
        "payment_method": transaction["payment_method"],
        "failure_reason": transaction["failure_reason"],
        "attempt_count": transaction["attempt_count"],
        "transaction_timestamp": transaction["transaction_timestamp"],
        "merchant_category": transaction["merchant_category"],
        "recommended_action": decision["recommended_action"],
        "recovery_probability": decision["recovery_probability"],
        "confidence": decision["confidence"],
        "priority": _priority(transaction, analysis, customer),
    }


@router.get("/transactions")
def list_transactions(
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    failure_reason: Optional[str] = None,
    action: Optional[str] = None,
) -> dict[str, Any]:
    """List observable transactions with their guarded SecondChance decisions."""
    transactions, customers, _ = get_dataset()
    items = []
    decisions = get_secondchance_decisions()
    for transaction in transactions:
        analysis, _, decision = decisions[transaction["transaction_id"]]
        if failure_reason and transaction["failure_reason"] != failure_reason:
            continue
        if action and decision["recommended_action"] != action:
            continue
        items.append(_transaction_item(transaction, decision, analysis, customers[transaction["customer_id"]]))
    return {"total": len(items), "limit": limit, "offset": offset, "items": items[offset : offset + limit]}


@router.get("/transactions/{transaction_id}")
def get_transaction(transaction_id: str) -> dict[str, Any]:
    """Return an observable transaction investigation and its guardrails."""
    transactions, customers, _ = get_dataset()
    transaction = next(
        (item for item in transactions if item["transaction_id"] == transaction_id), None
    )
    if transaction is None:
        raise HTTPException(status_code=404, detail="Transaction not found")
    customer = customers.get(transaction["customer_id"])
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer profile not found")
    cached = get_secondchance_decisions()
    analysis, guardrails, decision = cached.get(transaction_id) or secondchance_decision(transaction, customer)
    public_analysis = _public_analysis(analysis)
    public_analysis["recommended_action"] = decision["recommended_action"]
    return {
        "transaction": transaction,
        "customer_profile": customer,
        "analysis": public_analysis,
        "guardrails": guardrails,
    }


@intelligence_router.post("/analyze")
def analyze(request: AnalyzeRequest) -> dict[str, Any]:
    """Analyze supplied observable data without running a simulation."""
    transaction = request.transaction.model_dump(mode="json")
    customer = request.customer_profile.model_dump(mode="json")
    analysis, guardrails, decision = secondchance_decision(transaction, customer)
    public_analysis = _public_analysis(analysis)
    public_analysis["recommended_action"] = decision["recommended_action"]
    return {"analysis": public_analysis, "guardrails": guardrails}


@intelligence_router.get("/intelligence/summary")
def intelligence_summary() -> dict[str, Any]:
    """Aggregate observable intelligence without exposing simulation truth."""
    return _intelligence_summary()


@lru_cache(maxsize=1)
def _intelligence_summary() -> dict[str, Any]:
    """Cache aggregates because the bundled synthetic dataset is immutable at runtime."""
    transactions, customers, _ = get_dataset()
    failures: dict[str, dict[str, float]] = defaultdict(lambda: {"count": 0, "revenue": 0.0})
    methods: dict[str, dict[str, float]] = defaultdict(lambda: {"count": 0, "revenue": 0.0})
    actions: dict[str, dict[str, float]] = defaultdict(lambda: {"count": 0, "expected_value": 0.0})
    priority = defaultdict(int)
    opportunities = high_value = 0
    model: dict[str, Any] | None = None
    total_revenue = 0.0
    decisions = get_secondchance_decisions()
    for transaction in transactions:
        analysis, _, decision = decisions[transaction["transaction_id"]]
        amount = float(transaction["amount"])
        total_revenue += amount
        failures[transaction["failure_reason"]]["count"] += 1
        failures[transaction["failure_reason"]]["revenue"] += amount
        methods[transaction["payment_method"]]["count"] += 1
        methods[transaction["payment_method"]]["revenue"] += amount
        action = decision["recommended_action"]
        actions[action]["count"] += 1
        actions[action]["expected_value"] += float(analysis["expected_action_values"].get(action, 0))
        expected_value = amount * float(analysis["recovery_probability"])
        level = "CRITICAL" if expected_value >= 20_000 else "HIGH" if expected_value >= 9_000 else "MEDIUM" if expected_value >= 3_000 else "LOW"
        priority[level] += 1
        opportunities += int(analysis["recovery_probability"] >= .5 and action != "STOP_RECOVERY")
        high_value += int(amount >= 15_000)
        model = analysis["model"]
    return {"transactions_analyzed": len(transactions), "recovery_opportunity_count": opportunities, "high_value_count": high_value, "total_revenue_at_risk": round(total_revenue, 2), "failure_reason_distribution": failures, "payment_method_metrics": methods, "action_distribution": actions, "priority_distribution": dict(priority), "model": model}
