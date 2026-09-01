from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel


class Transaction(BaseModel):
    transaction_id: str
    customer_id: str
    amount: float
    currency: str
    payment_method: str
    failure_reason: str
    attempt_count: int
    transaction_timestamp: datetime
    merchant_category: str


class CustomerProfile(BaseModel):
    customer_id: str
    tenure_days: int
    total_transactions: int
    successful_transactions: int
    payment_success_rate: float
    average_transaction_amount: float
    previous_recovery_success_rate: float
    contacts_last_7_days: int


class RecoveryAction(str, Enum):
    RETRY_NOW = "RETRY_NOW"
    RETRY_LATER = "RETRY_LATER"
    SEND_REMINDER = "SEND_REMINDER"
    UPDATE_PAYMENT_METHOD = "UPDATE_PAYMENT_METHOD"
    ESCALATE_TO_HUMAN = "ESCALATE_TO_HUMAN"
    STOP_RECOVERY = "STOP_RECOVERY"


class AgentDecision(BaseModel):
    transaction_id: str
    diagnosis: str
    recovery_probability: float
    recommended_action: RecoveryAction
    recommended_delay_minutes: Optional[int] = None
    confidence: float
    reasoning: list[str]
