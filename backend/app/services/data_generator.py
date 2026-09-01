"""Deterministic synthetic data for local recovery simulations.

The simulation truth emitted here is deliberately separate from observable
transaction and customer data. It should only be consumed by the simulator.
"""

from __future__ import annotations

import json
import random
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from app.models.schemas import CustomerProfile, RecoveryAction, Transaction


DATASET_SEED = 20260901
DATA_DIR = Path(__file__).resolve().parents[2] / "data"

PERSONA_WEIGHTS = {
    "RETRY_RESPONSIVE": 25,
    "SALARY_CYCLE": 15,
    "REMINDER_RESPONSIVE": 15,
    "PAYMENT_METHOD_ISSUE": 15,
    "HIGH_VALUE_SENSITIVE": 10,
    "LOW_RECOVERY": 20,
}

ACTION_PROBABILITIES: dict[str, dict[RecoveryAction, float]] = {
    "RETRY_RESPONSIVE": {RecoveryAction.RETRY_NOW: 0.65, RecoveryAction.RETRY_LATER: 0.92, RecoveryAction.SEND_REMINDER: 0.25, RecoveryAction.UPDATE_PAYMENT_METHOD: 0.10, RecoveryAction.ESCALATE_TO_HUMAN: 0.30, RecoveryAction.STOP_RECOVERY: 0.0},
    "SALARY_CYCLE": {RecoveryAction.RETRY_NOW: 0.10, RecoveryAction.RETRY_LATER: 0.85, RecoveryAction.SEND_REMINDER: 0.35, RecoveryAction.UPDATE_PAYMENT_METHOD: 0.05, RecoveryAction.ESCALATE_TO_HUMAN: 0.25, RecoveryAction.STOP_RECOVERY: 0.0},
    "REMINDER_RESPONSIVE": {RecoveryAction.RETRY_NOW: 0.20, RecoveryAction.RETRY_LATER: 0.35, RecoveryAction.SEND_REMINDER: 0.88, RecoveryAction.UPDATE_PAYMENT_METHOD: 0.10, RecoveryAction.ESCALATE_TO_HUMAN: 0.30, RecoveryAction.STOP_RECOVERY: 0.0},
    "PAYMENT_METHOD_ISSUE": {RecoveryAction.RETRY_NOW: 0.05, RecoveryAction.RETRY_LATER: 0.15, RecoveryAction.SEND_REMINDER: 0.40, RecoveryAction.UPDATE_PAYMENT_METHOD: 0.90, RecoveryAction.ESCALATE_TO_HUMAN: 0.35, RecoveryAction.STOP_RECOVERY: 0.0},
    "HIGH_VALUE_SENSITIVE": {RecoveryAction.RETRY_NOW: 0.20, RecoveryAction.RETRY_LATER: 0.35, RecoveryAction.SEND_REMINDER: 0.40, RecoveryAction.UPDATE_PAYMENT_METHOD: 0.30, RecoveryAction.ESCALATE_TO_HUMAN: 0.90, RecoveryAction.STOP_RECOVERY: 0.0},
    "LOW_RECOVERY": {RecoveryAction.RETRY_NOW: 0.05, RecoveryAction.RETRY_LATER: 0.08, RecoveryAction.SEND_REMINDER: 0.10, RecoveryAction.UPDATE_PAYMENT_METHOD: 0.08, RecoveryAction.ESCALATE_TO_HUMAN: 0.12, RecoveryAction.STOP_RECOVERY: 0.0},
}

OPTIMAL_ACTIONS = {
    "RETRY_RESPONSIVE": RecoveryAction.RETRY_LATER,
    "SALARY_CYCLE": RecoveryAction.RETRY_LATER,
    "REMINDER_RESPONSIVE": RecoveryAction.SEND_REMINDER,
    "PAYMENT_METHOD_ISSUE": RecoveryAction.UPDATE_PAYMENT_METHOD,
    "HIGH_VALUE_SENSITIVE": RecoveryAction.ESCALATE_TO_HUMAN,
    "LOW_RECOVERY": RecoveryAction.STOP_RECOVERY,
}


def _persona_sequence(count: int, rng: random.Random) -> list[str]:
    """Allocate personas using the requested percentages and shuffle them."""
    allocations = {persona: count * weight // 100 for persona, weight in PERSONA_WEIGHTS.items()}
    remainder = count - sum(allocations.values())
    candidates = sorted(PERSONA_WEIGHTS, key=lambda item: (count * PERSONA_WEIGHTS[item] % 100, PERSONA_WEIGHTS[item]), reverse=True)
    for persona in candidates[:remainder]:
        allocations[persona] += 1
    personas = [persona for persona, amount in allocations.items() for _ in range(amount)]
    rng.shuffle(personas)
    return personas


def _choice(rng: random.Random, options: list[tuple[str, int]]) -> str:
    values, weights = zip(*options)
    return rng.choices(values, weights=weights, k=1)[0]


def _failure_reason(persona: str, rng: random.Random) -> str:
    options = {
        "RETRY_RESPONSIVE": [("BANK_TIMEOUT", 60), ("NETWORK_ERROR", 35), ("PAYMENT_DECLINED", 5)],
        "SALARY_CYCLE": [("INSUFFICIENT_FUNDS", 100)],
        "REMINDER_RESPONSIVE": [("USER_ABANDONED", 55), ("PAYMENT_DECLINED", 40), ("NETWORK_ERROR", 5)],
        "PAYMENT_METHOD_ISSUE": [("CARD_EXPIRED", 55), ("MANDATE_FAILED", 40), ("PAYMENT_DECLINED", 5)],
        "HIGH_VALUE_SENSITIVE": [("PAYMENT_DECLINED", 60), ("BANK_TIMEOUT", 35), ("NETWORK_ERROR", 5)],
        "LOW_RECOVERY": [("PAYMENT_DECLINED", 80), ("INSUFFICIENT_FUNDS", 15), ("USER_ABANDONED", 5)],
    }
    return _choice(rng, options[persona])


def _observable_values(persona: str, rng: random.Random) -> tuple[float, int, float, int]:
    ranges = {
        "RETRY_RESPONSIVE": ((0.85, 0.98), (1, 2), (0.70, 0.95), (0, 1)),
        "SALARY_CYCLE": ((0.65, 0.90), (1, 2), (0.45, 0.80), (0, 1)),
        "REMINDER_RESPONSIVE": ((0.60, 0.88), (1, 2), (0.40, 0.75), (0, 2)),
        "PAYMENT_METHOD_ISSUE": ((0.55, 0.85), (2, 3), (0.20, 0.60), (1, 2)),
        "HIGH_VALUE_SENSITIVE": ((0.80, 0.98), (2, 3), (0.30, 0.70), (1, 2)),
        "LOW_RECOVERY": ((0.20, 0.60), (3, 4), (0.00, 0.25), (2, 4)),
    }
    success_rate, attempts, recovery_rate, contacts = ranges[persona]
    return round(rng.uniform(*success_rate), 2), rng.randint(*attempts), round(rng.uniform(*recovery_rate), 2), rng.randint(*contacts)


def generate_dataset(count: int = 500) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Generate observable records and simulator-only truth for failed payments."""
    if count < 0:
        raise ValueError("count must be non-negative")
    rng = random.Random(DATASET_SEED)
    # Anchoring at midnight keeps repeated calls on the same day reproducible.
    anchor = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    transactions: list[dict[str, Any]] = []
    customer_profiles: list[dict[str, Any]] = []
    simulation_truth: list[dict[str, Any]] = []

    for index, persona in enumerate(_persona_sequence(count, rng), start=1):
        transaction_id, customer_id = f"TXN_{index:04d}", f"CUST_{index:04d}"
        success_rate, attempt_count, previous_recovery_rate, contacts = _observable_values(persona, rng)
        failure_reason = _failure_reason(persona, rng)
        amount = round(rng.uniform(10000, 50000) if persona == "HIGH_VALUE_SENSITIVE" else rng.uniform(199, 9999), 2)
        total_transactions = rng.randint(8, 120)
        transaction = Transaction(
            transaction_id=transaction_id, customer_id=customer_id, amount=amount, currency="INR",
            payment_method="CARD" if failure_reason == "CARD_EXPIRED" else rng.choice(["UPI", "CARD", "NETBANKING", "WALLET"]),
            failure_reason=failure_reason, attempt_count=attempt_count,
            transaction_timestamp=anchor - timedelta(days=rng.randint(0, 29), minutes=rng.randint(0, 1439)),
            merchant_category=rng.choice(["E_COMMERCE", "SAAS", "SUBSCRIPTION", "MARKETPLACE"]),
        )
        profile = CustomerProfile(
            customer_id=customer_id, tenure_days=rng.randint(30, 1825), total_transactions=total_transactions,
            successful_transactions=round(total_transactions * success_rate), payment_success_rate=success_rate,
            average_transaction_amount=round(amount * rng.uniform(0.65, 1.35), 2),
            previous_recovery_success_rate=previous_recovery_rate, contacts_last_7_days=contacts,
        )
        transactions.append(transaction.model_dump(mode="json"))
        customer_profiles.append(profile.model_dump(mode="json"))
        simulation_truth.append({
            "transaction_id": transaction_id,
            "hidden_persona": persona,
            "optimal_action": OPTIMAL_ACTIONS[persona].value,
            "action_success_probabilities": {action.value: probability for action, probability in ACTION_PROBABILITIES[persona].items()},
            "simulation_seed": rng.randrange(1, 2**31),
        })
    return transactions, customer_profiles, simulation_truth


def save_dataset(count: int = 500) -> tuple[Path, Path, Path]:
    """Generate and persist the local JSON datasets, returning their paths."""
    transactions, customer_profiles, simulation_truth = generate_dataset(count)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    paths = (DATA_DIR / "transactions.json", DATA_DIR / "customer_profiles.json", DATA_DIR / "simulation_truth.json")
    for path, data in zip(paths, (transactions, customer_profiles, simulation_truth)):
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return paths


def load_dataset() -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Load the observable data and simulator-only truth from local JSON files."""
    paths = (DATA_DIR / "transactions.json", DATA_DIR / "customer_profiles.json", DATA_DIR / "simulation_truth.json")
    transactions, customer_profiles, simulation_truth = (json.loads(path.read_text(encoding="utf-8")) for path in paths)
    return transactions, customer_profiles, simulation_truth


if __name__ == "__main__":
    generated_transactions, _, generated_truth = generate_dataset()
    output_paths = save_dataset()
    print(f"Total transactions: {len(generated_transactions)}")
    print(f"Persona distribution: {dict(sorted(Counter(item['hidden_persona'] for item in generated_truth).items()))}")
    print("Output files:")
    for output_path in output_paths:
        print(f"- {output_path}")
