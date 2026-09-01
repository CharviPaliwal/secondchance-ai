"""Observable transaction and intelligence endpoints."""

from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.models.schemas import CustomerProfile, Transaction
from app.services.workflows import get_dataset, secondchance_decision


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
    }


def _transaction_item(transaction: dict[str, Any], decision: dict[str, Any]) -> dict[str, Any]:
    """Build the compact observable transaction response item."""
    return {
        "transaction_id": transaction["transaction_id"],
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
    for transaction in transactions:
        _, _, decision = secondchance_decision(
            transaction, customers[transaction["customer_id"]]
        )
        if failure_reason and transaction["failure_reason"] != failure_reason:
            continue
        if action and decision["recommended_action"] != action:
            continue
        items.append(_transaction_item(transaction, decision))
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
    analysis, guardrails, decision = secondchance_decision(transaction, customer)
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
